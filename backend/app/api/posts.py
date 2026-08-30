"""论坛 API：帖子/回帖/投票/采纳/状态/代码片段/讨论绑定"""

from flask import Blueprint, request, g

from app.extensions import db
from app.models import (
    Post,
    PostReply,
    PostVote,
    CodeSnippet,
    DiscussionLink,
    POST_CATEGORIES,
    POST_STATUSES,
)
from app.services import activity, post as post_service, discussion as discussion_service
from app.services.notification import create_notification
from app.services.git_service import GitService, GitServiceError
from app.utils.decorators import (
    login_required,
    project_from_slug,
    member_role,
    project_visible,
    is_owner_or_admin,
)

bp = Blueprint("posts", __name__, url_prefix="/api/projects/<string:slug>/posts")


def _check_access(slug, min_role="viewer"):
    project = project_from_slug(slug)
    role = member_role(g.user, project)
    if not project_visible(project, role):
        return None, None, "无权访问该项目", 403
    return project, role, None, None


def _notify_mention(project, obj, actor_id, content):
    """解析 @提及 并发送通知"""
    for user in post_service.parse_mentions(content):
        if user.id == actor_id:
            continue
        if isinstance(obj, Post):
            url = f"/projects/{project.slug}/posts/{obj.id}"
        else:
            url = f"/projects/{project.slug}/posts/{obj.post_id}#reply-{obj.id}"
        create_notification(
            user_id=user.id,
            type_="mention",
            title=f"{g.user.full_name} 在帖子中提到了你",
            content=(obj.title if isinstance(obj, Post) else obj.post.title)[:200],
            project_id=project.id,
            url=url,
        )


def _save_snippets(project, post_id, reply_id, snippets, content=None):
    """保存编辑器传来的代码片段（含从仓库拉取的内容），并将正文占位符替换为真实 ID"""
    created = []
    mapping = {}
    for idx, sn in enumerate(snippets or []):
        file_path = (sn.get("file_path") or "").strip() or None
        snippet_content = (sn.get("content") or "").strip()
        language = (sn.get("language") or "").strip() or "plaintext"
        start_line = sn.get("start_line")
        end_line = sn.get("end_line")
        if not snippet_content and file_path:
            try:
                repo = GitService.open(project.id)
                data, _ = repo.blob_content(file_path)
                snippet_content = data.decode("utf-8", errors="replace")
                language = post_service.guess_language(file_path)
            except GitServiceError:
                return None, None, "从仓库读取文件失败"
        if not snippet_content:
            continue
        s = post_service.create_snippet(
            post_id, reply_id, project.id, file_path, language, start_line, end_line, snippet_content
        )
        created.append(s)
        mapping[idx] = s.id
    if content is not None and mapping:
        for idx, real in mapping.items():
            content = content.replace(f":::snippet:{idx}:::", f":::snippet:{real}:::")
    return created, content, None


# ---------- 帖子 ----------

@bp.get("")
@login_required
def list_posts(slug):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    category = request.args.get("category", "all")
    status = request.args.get("status", "all")
    q = request.args.get("q", "")
    sort = request.args.get("sort", "latest")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    total, posts = post_service.query_posts(
        project.id, category=category, status=status, q=q, sort=sort, page=page, per_page=per_page
    )
    # N+1 优化：批量查询当前用户的投票状态
    post_ids = [p.id for p in posts]
    my_votes = set()
    if post_ids:
        my_votes = {
            v.target_id
            for v in PostVote.query.filter(
                PostVote.user_id == g.user.id,
                PostVote.target_type == "post",
                PostVote.target_id.in_(post_ids),
            ).all()
        }
    return {
        "total": total,
        "items": [p.to_dict(viewer_id=g.user.id, my_votes=my_votes) for p in posts],
        "page": page,
        "per_page": per_page,
    }


@bp.post("")
@login_required
def create_post(slug):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    category = data.get("category") or "other"
    if not title:
        return {"error": "请填写帖子标题"}, 400
    if not content:
        return {"error": "请填写帖子内容"}, 400
    if category not in POST_CATEGORIES:
        return {"error": "帖子分类不合法"}, 400

    post = Post(
        project_id=project.id,
        author_id=g.user.id,
        title=title,
        category=category,
        content=content,
    )
    db.session.add(post)
    db.session.flush()

    snippets, content, err = _save_snippets(project, post.id, None, data.get("snippets"), content)
    if err:
        db.session.rollback()
        return {"error": err}, 400
    post.content = content

    # 讨论绑定（可选：绑定的 commit/文件/行）
    bindings = data.get("bindings") or []
    if data.get("binding"):  # 兼容单个绑定
        bindings.append(data["binding"])
    for b in bindings:
        try:
            discussion_service.create_link(
                project.id,
                post.id,
                commit_sha=(b.get("commit_sha") or None),
                file_path=(b.get("file_path") or None),
                line_start=b.get("line_start"),
                line_end=b.get("line_end"),
            )
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

    _notify_mention(project, post, g.user.id, content)
    activity.record_event(
        project.id, g.user.id, "post", "created",
        title=f"发布帖子：{title}",
        data={"post_id": post.id, "category": category},
    )
    db.session.commit()
    return {"post": post.to_dict(detail=True, viewer_id=g.user.id)}, 201


@bp.get("/<int:post_id>")
@login_required
def get_post(slug, post_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    post = Post.query.filter_by(id=post_id, project_id=project.id).first()
    if post is None:
        return {"error": "帖子不存在"}, 404
    return {"post": post.to_dict(detail=True, viewer_id=g.user.id)}


@bp.put("/<int:post_id>")
@login_required
def update_post(slug, post_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    post = Post.query.filter_by(id=post_id, project_id=project.id).first()
    if post is None:
        return {"error": "帖子不存在"}, 404
    if post.author_id != g.user.id and not is_owner_or_admin(project, g.user):
        return {"error": "仅作者可以编辑帖子"}, 403
    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"]:
        post.title = (data["title"] or "").strip()
    if "content" in data and data["content"]:
        post.content = (data["content"] or "").strip()
    if "category" in data and data["category"] in POST_CATEGORIES:
        post.category = data["category"]
    if "status" in data and data["status"] in POST_STATUSES:
        try:
            post_service.set_post_status(g.user, project, post, data["status"])
        except PermissionError as e:
            return {"error": str(e)}, 403
    if "snippets" in data:
        old_ids = [s.id for s in post.snippets]
        if old_ids:
            CodeSnippet.query.filter(CodeSnippet.id.in_(old_ids)).delete(synchronize_session=False)
        _, post.content, err = _save_snippets(project, post.id, None, data["snippets"], post.content)
        if err:
            db.session.rollback()
            return {"error": err}, 400
    db.session.commit()
    return {"post": post.to_dict(detail=True, viewer_id=g.user.id)}


@bp.delete("/<int:post_id>")
@login_required
def delete_post(slug, post_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    post = Post.query.filter_by(id=post_id, project_id=project.id).first()
    if post is None:
        return {"error": "帖子不存在"}, 404
    if post.author_id != g.user.id and not is_owner_or_admin(project, g.user):
        return {"error": "仅作者或管理员可以删除帖子"}, 403
    from app.services import audit

    audit.record("delete_post", "post", post.id, {"title": post.title, "project_id": project.id})
    db.session.delete(post)
    activity.record_event(
        project.id, g.user.id, "post", "deleted", title=f"删除帖子：{post.title}"
    )
    db.session.commit()
    return {"ok": True}


# ---------- 投票 ----------

@bp.post("/<int:post_id>/vote")
@login_required
def vote_post(slug, post_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    post = Post.query.filter_by(id=post_id, project_id=project.id).first()
    if post is None:
        return {"error": "帖子不存在"}, 404
    try:
        count, voted = post_service.toggle_vote(g.user.id, "post", post.id)
    except ValueError as e:
        return {"error": str(e)}, 400
    db.session.commit()
    return {"vote_count": count, "voted": voted}


# ---------- 回帖 ----------

@bp.get("/<int:post_id>/replies")
@login_required
def list_replies(slug, post_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    post = Post.query.filter_by(id=post_id, project_id=project.id).first()
    if post is None:
        return {"error": "帖子不存在"}, 404
    return {"replies": [r.to_dict(viewer_id=g.user.id) for r in post.replies]}


@bp.post("/<int:post_id>/replies")
@login_required
def create_reply(slug, post_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    post = Post.query.filter_by(id=post_id, project_id=project.id).first()
    if post is None:
        return {"error": "帖子不存在"}, 404
    if post.status == "closed":
        return {"error": "帖子已关闭，无法回帖"}, 400
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return {"error": "回帖内容不能为空"}, 400

    reply = PostReply(post_id=post.id, author_id=g.user.id, content=content)
    db.session.add(reply)
    db.session.flush()
    post.reply_count += 1

    snippets, content, err = _save_snippets(project, None, reply.id, data.get("snippets"), content)
    if err:
        db.session.rollback()
        return {"error": err}, 400
    reply.content = content

    for b in data.get("bindings") or []:
        try:
            discussion_service.create_link(
                project.id,
                post.id,
                reply_id=reply.id,
                commit_sha=(b.get("commit_sha") or None),
                file_path=(b.get("file_path") or None),
                line_start=b.get("line_start"),
                line_end=b.get("line_end"),
            )
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

    _notify_mention(project, post, g.user.id, content)
    # 通知帖子作者
    if post.author_id != g.user.id:
        create_notification(
            user_id=post.author_id,
            type_="comment",
            title=f"{g.user.full_name} 回复了你的帖子：{post.title}",
            content=(content or "")[:200],
            project_id=project.id,
            url=f"/projects/{project.slug}/posts/{post.id}",
        )
    activity.record_event(
        project.id, g.user.id, "post", "replied",
        title=f"回复帖子：{post.title}",
        data={"post_id": post.id},
    )
    # 回复历史快照（帖子删除后仍保留）
    from app.models import UserReplyRecord

    db.session.add(
        UserReplyRecord(
            user_id=g.user.id,
            scope="project",
            project_id=project.id,
            project_slug=project.slug,
            post_id=post.id,
            post_title=post.title,
            reply_id=reply.id,
            content_snippet=(content or "")[:100],
        )
    )
    db.session.commit()
    return {"reply": reply.to_dict(viewer_id=g.user.id)}, 201


@bp.put("/<int:post_id>/replies/<int:reply_id>")
@login_required
def update_reply(slug, post_id, reply_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    reply = PostReply.query.filter_by(id=reply_id, post_id=post_id).first()
    if reply is None:
        return {"error": "回帖不存在"}, 404
    if reply.author_id != g.user.id:
        return {"error": "仅作者可以编辑回帖"}, 403
    data = request.get_json(silent=True) or {}
    if "content" in data and data["content"]:
        reply.content = (data["content"] or "").strip()
    db.session.commit()
    return {"reply": reply.to_dict(viewer_id=g.user.id)}


@bp.delete("/<int:post_id>/replies/<int:reply_id>")
@login_required
def delete_reply(slug, post_id, reply_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    post = Post.query.filter_by(id=post_id, project_id=project.id).first()
    if post is None:
        return {"error": "帖子不存在"}, 404
    reply = PostReply.query.filter_by(id=reply_id, post_id=post_id).first()
    if reply is None:
        return {"error": "回帖不存在"}, 404
    if reply.author_id != g.user.id and not is_owner_or_admin(project, g.user):
        return {"error": "仅作者或管理员可以删除回帖"}, 403
    if reply.is_accepted:
        post.accepted_reply_id = None
        post.status = "open"
    post.reply_count = max(0, post.reply_count - 1)
    from app.services import audit

    audit.record("delete_reply", "reply", reply.id, {"post_id": post.id, "project_id": project.id})
    db.session.delete(reply)
    db.session.commit()
    return {"ok": True}


@bp.post("/<int:post_id>/replies/<int:reply_id>/vote")
@login_required
def vote_reply(slug, post_id, reply_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    reply = PostReply.query.filter_by(id=reply_id, post_id=post_id).first()
    if reply is None:
        return {"error": "回帖不存在"}, 404
    try:
        count, voted = post_service.toggle_vote(g.user.id, "reply", reply.id)
    except ValueError as e:
        return {"error": str(e)}, 400
    db.session.commit()
    return {"vote_count": count, "voted": voted}


@bp.post("/<int:post_id>/replies/<int:reply_id>/accept")
@login_required
def accept_reply(slug, post_id, reply_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    post = Post.query.filter_by(id=post_id, project_id=project.id).first()
    if post is None:
        return {"error": "帖子不存在"}, 404
    reply = PostReply.query.filter_by(id=reply_id, post_id=post_id).first()
    if reply is None:
        return {"error": "回帖不存在"}, 404
    try:
        post_service.accept_reply(g.user, project, post, reply)
    except PermissionError as e:
        return {"error": str(e)}, 403
    activity.record_event(
        project.id, g.user.id, "post", "solved",
        title=f"采纳回答：{post.title}",
        data={"post_id": post.id, "reply_id": reply.id},
    )
    db.session.commit()
    return {"post": post.to_dict(detail=True, viewer_id=g.user.id)}


@bp.post("/<int:post_id>/status")
@login_required
def change_status(slug, post_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    post = Post.query.filter_by(id=post_id, project_id=project.id).first()
    if post is None:
        return {"error": "帖子不存在"}, 404
    data = request.get_json(silent=True) or {}
    try:
        post_service.set_post_status(g.user, project, post, data.get("status", ""))
    except PermissionError as e:
        return {"error": str(e)}, 403
    except ValueError as e:
        return {"error": str(e)}, 400
    db.session.commit()
    return {"post": post.to_dict(detail=True, viewer_id=g.user.id)}


# ---------- 讨论绑定 ----------

@bp.get("/<int:post_id>/discussion-links")
@login_required
def post_links(slug, post_id):
    """帖子关联的绑定列表（含代码上下文）"""
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    links = DiscussionLink.query.filter_by(project_id=project.id, post_id=post_id).all()
    return {"items": [discussion_service.post_with_context(l) for l in links]}


@bp.delete("/<int:post_id>/discussion-links/<int:link_id>")
@login_required
def delete_link(slug, post_id, link_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    link = DiscussionLink.query.filter_by(id=link_id, project_id=project.id).first()
    if link is None:
        return {"error": "绑定不存在"}, 404
    post = Post.query.get(link.post_id)
    if not (post and post.author_id == g.user.id) and not is_owner_or_admin(project, g.user):
        return {"error": "无权删除绑定"}, 403
    db.session.delete(link)
    db.session.commit()
    return {"ok": True}
