"""讨论绑定服务：帖子/回帖 ↔ Commit / 文件 / 行，双向查询与上下文渲染"""

from flask import current_app

from app.extensions import db
from app.models import DiscussionLink, Post, PostReply
from app.services.git_service import GitService, GitServiceError


def create_link(project_id, post_id, reply_id=None, commit_sha=None, file_path=None,
                line_start=None, line_end=None):
    if not commit_sha and not file_path:
        raise ValueError("绑定需指定 Commit 或文件路径")
    link = DiscussionLink(
        project_id=project_id,
        post_id=post_id,
        reply_id=reply_id,
        commit_sha=commit_sha,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
    )
    db.session.add(link)
    db.session.flush()
    return link


def query_by_commit(project_id, commit_sha):
    return (
        DiscussionLink.query.filter_by(project_id=project_id, commit_sha=commit_sha)
        .order_by(DiscussionLink.id.desc())
        .all()
    )


def query_by_file(project_id, file_path):
    return (
        DiscussionLink.query.filter_by(project_id=project_id, file_path=file_path)
        .order_by(DiscussionLink.id.desc())
        .all()
    )


def query_file_commit_links(project_id, commit_sha, file_path):
    """文件页展示：该提交中该文件的讨论（文件绑定 + 行级绑定）"""
    return (
        DiscussionLink.query.filter_by(project_id=project_id, commit_sha=commit_sha, file_path=file_path)
        .order_by(DiscussionLink.line_start.asc(), DiscussionLink.id.desc())
        .all()
    )


def link_context(link):
    """绑定上下文：渲染帖子详情中的代码片段 / commit 信息"""
    context = {"kind": None}
    if link.commit_sha:
        try:
            repo = GitService.open(link.project_id)
            commit = repo.commit_detail(link.commit_sha)
            context = {
                "kind": "commit",
                "commit": commit,
                "file_path": link.file_path,
                "line_start": link.line_start,
                "line_end": link.line_end,
            }
        except (GitServiceError, Exception):
            context = {"kind": "commit", "commit": None, "sha": link.commit_sha}
    if link.file_path:
        try:
            repo = GitService.open(link.project_id)
            data, size = repo.blob_content(link.file_path, ref=link.commit_sha)
            lines = data.decode("utf-8", errors="replace").splitlines()
            start = (link.line_start or 1) - 1
            end = min(link.line_end or (start + 1), len(lines))
            selected = lines[start:end]
            context["kind"] = "file" if not link.commit_sha else "commit_file"
            context["file_path"] = link.file_path
            context["line_start"] = start + 1
            context["line_end"] = end
            context["code"] = "\n".join(selected)
            context["total_lines"] = len(lines)
        except (GitServiceError, Exception):
            context["kind"] = "file" if not link.commit_sha else "commit_file"
            context["file_path"] = link.file_path
            context["line_start"] = link.line_start
            context["line_end"] = link.line_end
            context["code"] = None
    return context


def post_with_context(link):
    """绑定列表项 + 帖子信息"""
    data = link.to_dict()
    data["post"] = None
    post = link.post
    if post:
        data["post"] = {
            "id": post.id,
            "title": post.title,
            "category": post.category,
            "author": post.author.to_dict(detail=False) if post.author else None,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "status": post.status,
        }
    data["context"] = link_context(link)
    return data
