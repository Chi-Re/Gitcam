"""社区论坛 API（全站板块）：浏览公开、操作需登录、代码片段仅公共仓库"""

from flask import Blueprint, request, g

from app.extensions import db
from app.models import (
    CommunityPost,
    CommunityReply,
    CommunitySnippet,
    Project,
)
from app.services import community as community_service
from app.services.git_service import GitService, GitServiceError
from app.services.notification import create_notification
from app.utils.decorators import login_required, load_current_user

bp = Blueprint("community", __name__, url_prefix="/api/community")


def _current_user():
    load_current_user()
    return g.user


def _notify_mentions(post, actor, content):
    for user in community_service.parse_mentions(content):
        if user.id == actor.id:
            continue
        create_notification(
            user_id=user.id,
            type_="mention",
            title=f"{actor.full_name} 在社区帖子中提到了你",
            content=post.title[:200],
            url=f"/community/{post.id}",
        )


def _save_snippets(post_id, reply_id, snippets, content=None):
    """保存片段：校验来源仓库必须为公共仓库；占位符替换为真实 ID"""
    created = []
    mapping = {}
    for idx, sn in enumerate(snippets or []):
        project = community_service.public_project_or_none(sn.get("project_id"))
        if project is None:
            return None, None, "只能引用公共仓库的代码"
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
                language = community_service.guess_language(file_path)
            except GitServiceError:
                return None, None, "从仓库读取文件失败"
        if not snippet_content:
            continue
        s = CommunitySnippet(
            post_id=post_id,
            reply_id=reply_id,
            project_id=project.id,
            file_path=file_path,
            language=language,
            start_line=start_line,
            end_line=end_line,
            content=snippet_content,
        )
        db.session.add(s)
        db.session.flush()
        created.append(s)
        mapping[idx] = s.id
    if content is not None and mapping:
        for idx, real in mapping.items():
            content = content.replace(f":::snippet:{idx}:::", f":::snippet:{real}:::")
    return created, content, None


# ---------- 公共仓库选择器 ----------

@bp.get("/public-projects")
def public_projects():
    """供发帖时选择来源：仅公共仓库"""
    projects = (
        Project.query.filter_by(visibility="public")
        .order_by(Project.updated_at.desc())
        .limit(50)
        .all()
    )
    return {
        "projects": [
            {"id": p.id, "slug": p.slug, "name": p.name, "description": p.description}
            for p in projects
        ]
    }


# ---------- 帖子（浏览公开） ----------

@bp.get("/posts")
def list_posts():
    category = request.args.get("category", "all")
    status = request.args.get("status", "all")
    q = request.args.get("q", "")
    sort = request.args.get("sort", "latest")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    user = _current_user()
    total, posts = community_service.query_posts(
        category=category, status=status, q=q, sort=sort, page=page, per_page=per_page
    )
    my_votes = community_service.batch_my_votes(user.id if user else None, [p.id for p in posts])
    return {
        "total": total,
        "items": [p.to_dict(viewer_id=user.id if user else None, my_votes=my_votes) for p in posts],
        "page": page,
        "per_page": per_page,
    }


@bp.post("/posts")
@login_required
def create_post():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    category = data.get("category") or "other"
    if not title:
        return {"error": "请填写帖子标题"}, 400
    if not content:
        return {"error": "请填写帖子内容"}, 400
    if category not in ("question", "share", "review", "announce", "other"):
        return {"error": "帖子分类不合法"}, 400

    post = CommunityPost(
        author_id=g.user.id, title=title, category=category, content=content
    )
    db.session.add(post)
    db.session.flush()

    _, content, err = _save_snippets(post.id, None, data.get("snippets"), content)
    if err:
        db.session.rollback()
        return {"error": err}, 400
    post.content = content

    _notify_mentions(post, g.user, content)
    db.session.commit()
    return {"post": post.to_dict(detail=True, viewer_id=g.user.id)}, 201


@bp.get("/posts/<int:post_id>")
def get_post(post_id):
    user = _current_user()
    post = CommunityPost.query.get(post_id)
    if post is None:
        return {"error": "帖子不存在"}, 404
    return {"post": post.to_dict(detail=True, viewer_id=user.id if user else None)}


@bp.put("/posts/<int:post_id>")
@login_required
def update_post(post_id):
    post = CommunityPost.query.get(post_id)
    if post is None:
        return {"error": "帖子不存在"}, 404
    if post.author_id != g.user.id and g.user.role != "admin":
        return {"error": "仅作者可以编辑帖子"}, 403
    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"]:
        post.title = (data["title"] or "").strip()
    if "content" in data and data["content"]:
        post.content = (data["content"] or "").strip()
    if "category" in data and data["category"] in ("question", "share", "review", "announce", "other"):
        post.category = data["category"]
    if "snippets" in data:
        old_ids = [s.id for s in post.snippets]
        if old_ids:
            CommunitySnippet.query.filter(CommunitySnippet.id.in_(old_ids)).delete(synchronize_session=False)
        _, post.content, err = _save_snippets(post.id, None, data["snippets"], post.content)
        if err:
            db.session.rollback()
            return {"error": err}, 400
    db.session.commit()
    return {"post": post.to_dict(detail=True, viewer_id=g.user.id)}


@bp.delete("/posts/<int:post_id>")
@login_required
def delete_post(post_id):
    post = CommunityPost.query.get(post_id)
    if post is None:
        return {"error": "帖子不存在"}, 404
    if post.author_id != g.user.id and g.user.role != "admin":
        return {"error": "仅作者或管理员可以删除帖子"}, 403
    from app.services import audit

    audit.record("delete_community_post", "community_post", post.id, {"title": post.title})
    db.session.delete(post)
    db.session.commit()
    return {"ok": True}


# ---------- 投票 / 状态 ----------

@bp.post("/posts/<int:post_id>/vote")
@login_required
def vote_post(post_id):
    post = CommunityPost.query.get(post_id)
    if post is None:
        return {"error": "帖子不存在"}, 404
    count, voted = community_service.toggle_vote(g.user.id, "post", post.id)
    db.session.commit()
    return {"vote_count": count, "voted": voted}


@bp.post("/posts/<int:post_id>/status")
@login_required
def change_status(post_id):
    post = CommunityPost.query.get(post_id)
    if post is None:
        return {"error": "帖子不存在"}, 404
    data = request.get_json(silent=True) or {}
    try:
        community_service.set_post_status(g.user, post, data.get("status", ""))
    except (PermissionError, ValueError) as e:
        return {"error": str(e)}, 400
    db.session.commit()
    return {"post": post.to_dict(detail=True, viewer_id=g.user.id)}


# ---------- 回帖 ----------

@bp.post("/posts/<int:post_id>/replies")
@login_required
def create_reply(post_id):
    post = CommunityPost.query.get(post_id)
    if post is None:
        return {"error": "帖子不存在"}, 404
    if post.status == "closed":
        return {"error": "帖子已关闭，无法回帖"}, 400
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return {"error": "回帖内容不能为空"}, 400

    reply = CommunityReply(post_id=post.id, author_id=g.user.id, content=content)
    db.session.add(reply)
    db.session.flush()
    post.reply_count += 1

    _, content, err = _save_snippets(None, reply.id, data.get("snippets"), content)
    if err:
        db.session.rollback()
        return {"error": err}, 400
    reply.content = content

    _notify_mentions(post, g.user, content)
    if post.author_id != g.user.id:
        create_notification(
            user_id=post.author_id,
            type_="comment",
            title=f"{g.user.full_name} 回复了你的社区帖子：{post.title}",
            content=(content or "")[:200],
            url=f"/community/{post.id}",
        )
    # 回复历史快照（帖子删除后仍保留）
    from app.models import UserReplyRecord

    db.session.add(
        UserReplyRecord(
            user_id=g.user.id,
            scope="community",
            post_id=post.id,
            post_title=post.title,
            reply_id=reply.id,
            content_snippet=(content or "")[:100],
        )
    )
    db.session.commit()
    return {"reply": reply.to_dict(viewer_id=g.user.id)}, 201


@bp.delete("/posts/<int:post_id>/replies/<int:reply_id>")
@login_required
def delete_reply(post_id, reply_id):
    post = CommunityPost.query.get(post_id)
    reply = CommunityReply.query.filter_by(id=reply_id, post_id=post_id).first()
    if reply is None:
        return {"error": "回帖不存在"}, 404
    if reply.author_id != g.user.id and g.user.role != "admin":
        return {"error": "仅作者或管理员可以删除回帖"}, 403
    if reply.is_accepted:
        post.accepted_reply_id = None
        post.status = "open"
    post.reply_count = max(0, post.reply_count - 1)
    db.session.delete(reply)
    db.session.commit()
    return {"ok": True}


@bp.post("/posts/<int:post_id>/replies/<int:reply_id>/vote")
@login_required
def vote_reply(post_id, reply_id):
    reply = CommunityReply.query.filter_by(id=reply_id, post_id=post_id).first()
    if reply is None:
        return {"error": "回帖不存在"}, 404
    count, voted = community_service.toggle_vote(g.user.id, "reply", reply.id)
    db.session.commit()
    return {"vote_count": count, "voted": voted}


@bp.post("/posts/<int:post_id>/replies/<int:reply_id>/accept")
@login_required
def accept_reply(post_id, reply_id):
    post = CommunityPost.query.get(post_id)
    if post is None:
        return {"error": "帖子不存在"}, 404
    reply = CommunityReply.query.filter_by(id=reply_id, post_id=post_id).first()
    if reply is None:
        return {"error": "回帖不存在"}, 404
    try:
        community_service.accept_reply(g.user, post, reply)
    except PermissionError as e:
        return {"error": str(e)}, 403
    db.session.commit()
    return {"post": post.to_dict(detail=True, viewer_id=g.user.id)}
