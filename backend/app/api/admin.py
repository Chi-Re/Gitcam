"""管理员后台 API：用户管理 / 内容管理 / 系统配置 / 日志审计（仅 admin 角色）"""

import os
import shutil

from flask import Blueprint, request, g, current_app

from app.extensions import db
from app.models import (
    User,
    Project,
    ProjectMember,
    Post,
    PostReply,
    Issue,
    IssueComment,
    ActivityEvent,
    SiteSetting,
    AuditLog,
    UserLoginLog,
    Notification,
    NotificationPref,
)
from app.services import activity, audit
from app.utils.decorators import roles_required, login_required

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _get_setting(key, default=None):
    s = SiteSetting.query.filter_by(key=key).first()
    return s.value if s else default


def _set_setting(key, value):
    s = SiteSetting.query.filter_by(key=key).first()
    if s is None:
        s = SiteSetting(key=key, value=str(value))
        db.session.add(s)
    else:
        s.value = str(value)


# ---------- 用户管理 ----------

@bp.get("/users")
@roles_required("admin")
def list_users():
    q = request.args.get("q", "")
    role = request.args.get("role", "")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            (User.username.like(like))
            | (User.email.like(like))
            | (User.full_name.like(like))
            | (User.student_id.like(like))
        )
    if role and role in ("student", "teacher", "admin"):
        query = query.filter_by(role=role)
    total = query.count()
    users = (
        query.order_by(User.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    )
    return {"total": total, "items": [u.to_dict() for u in users], "page": page, "per_page": per_page}


@bp.put("/users/<int:user_id>")
@roles_required("admin")
def update_user(user_id):
    user = User.query.get(user_id)
    if user is None:
        return {"error": "用户不存在"}, 404
    if user.id == g.user.id:
        return {"error": "不能修改自己的账号"}, 400
    data = request.get_json(silent=True) or {}
    if "role" in data:
        if data["role"] not in ("student", "teacher", "admin"):
            return {"error": "角色不合法"}, 400
        old = user.role
        user.role = data["role"]
        audit.record("change_role", "user", user.id, {"from": old, "to": data["role"], "username": user.username})
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
        audit.record(
            "ban_user" if not user.is_active else "unban_user",
            "user", user.id, {"username": user.username},
        )
    db.session.commit()
    return {"user": user.to_dict()}


# ---------- 内容管理 ----------

@bp.get("/projects")
@roles_required("admin")
def list_projects():
    q = request.args.get("q", "")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    query = Project.query
    if q:
        like = f"%{q}%"
        query = query.filter(Project.name.like(like) | Project.slug.like(like) | Project.description.like(like))
    total = query.count()
    projects = (
        query.order_by(Project.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    )
    return {"total": total, "items": [p.to_dict() for p in projects], "page": page, "per_page": per_page}


@bp.delete("/projects/<string:slug>")
@roles_required("admin")
def delete_project(slug):
    project = Project.query.filter_by(slug=slug).first()
    if project is None:
        return {"error": "项目不存在"}, 404
    repo_path = os.path.join(current_app.config["REPO_ROOT"], f"{project.id}.git")
    if os.path.isdir(repo_path):
        shutil.rmtree(repo_path, ignore_errors=True)
    ActivityEvent.query.filter_by(project_id=project.id).delete()
    ProjectMember.query.filter_by(project_id=project.id).delete()
    audit.record("delete_project", "project", project.id, {"slug": project.slug, "name": project.name})
    db.session.delete(project)
    db.session.commit()
    return {"ok": True}


@bp.get("/posts")
@roles_required("admin")
def list_posts():
    q = request.args.get("q", "")
    project_id = request.args.get("project_id", "")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    query = Post.query
    if q:
        query = query.filter(Post.title.like(f"%{q}%") | Post.content.like(f"%{q}%"))
    if project_id:
        query = query.filter_by(project_id=int(project_id))
    total = query.count()
    posts = (
        query.order_by(Post.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    )
    return {"total": total, "items": [p.to_dict() for p in posts], "page": page, "per_page": per_page}


@bp.delete("/posts/<int:post_id>")
@roles_required("admin")
def delete_post(post_id):
    post = Post.query.get(post_id)
    if post is None:
        return {"error": "帖子不存在"}, 404
    audit.record("delete_post", "post", post.id, {"title": post.title, "project_id": post.project_id})
    db.session.delete(post)
    db.session.commit()
    return {"ok": True}


@bp.delete("/posts/<int:post_id>/replies/<int:reply_id>")
@roles_required("admin")
def delete_reply(post_id, reply_id):
    post = Post.query.get(post_id)
    reply = PostReply.query.filter_by(id=reply_id, post_id=post_id).first()
    if reply is None:
        return {"error": "回帖不存在"}, 404
    if reply.is_accepted and post:
        post.accepted_reply_id = None
        post.status = "open"
    if post:
        post.reply_count = max(0, post.reply_count - 1)
    audit.record("delete_reply", "reply", reply.id, {"post_id": post_id})
    db.session.delete(reply)
    db.session.commit()
    return {"ok": True}


@bp.delete("/issues/<int:issue_id>/comments/<int:comment_id>")
@roles_required("admin")
def delete_issue_comment(issue_id, comment_id):
    comment = IssueComment.query.filter_by(id=comment_id, issue_id=issue_id).first()
    if comment is None:
        return {"error": "评论不存在"}, 404
    issue = Issue.query.get(issue_id)
    if issue:
        issue.comment_count = max(0, issue.comment_count - 1)
    audit.record("delete_issue_comment", "issue_comment", comment.id, {"issue_id": issue_id})
    db.session.delete(comment)
    db.session.commit()
    return {"ok": True}


# ---------- 系统配置 ----------

@bp.get("/settings")
@roles_required("admin")
def get_settings():
    return {
        "settings": {
            "site_announcement": _get_setting("site_announcement", ""),
            "notifications_enabled": _get_setting("notifications_enabled", "true") != "false",
            "storage_quota_mb": int(_get_setting("storage_quota_mb", "1024") or 1024),
        }
    }


@bp.put("/settings")
@roles_required("admin")
def update_settings():
    data = request.get_json(silent=True) or {}
    if "site_announcement" in data:
        _set_setting("site_announcement", (data["site_announcement"] or "")[:1000])
    if "notifications_enabled" in data:
        _set_setting("notifications_enabled", "true" if data["notifications_enabled"] else "false")
    if "storage_quota_mb" in data:
        quota = int(data["storage_quota_mb"] or 1024)
        _set_setting("storage_quota_mb", max(1, min(quota, 102400)))
    audit.record("update_settings", "settings", None, {k: v for k, v in data.items() if k in ("site_announcement", "notifications_enabled", "storage_quota_mb")})
    db.session.commit()
    return get_settings()


# ---------- 日志审计 ----------

@bp.get("/logs")
@roles_required("admin")
def logs():
    kind = request.args.get("type", "login")  # login / audit
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    if kind == "audit":
        model, user_attr = AuditLog, "actor"
        total = AuditLog.query.count()
        rows = AuditLog.query.order_by(AuditLog.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
        items = [r.to_dict() for r in rows]
    else:
        total = UserLoginLog.query.count()
        rows = UserLoginLog.query.order_by(UserLoginLog.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
        items = []
        for r in rows:
            user = User.query.get(r.user_id) if r.user_id else None
            items.append({
                "id": r.id,
                "user": user.username if user else None,
                "ip": r.ip,
                "user_agent": r.user_agent,
                "success": r.success,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
    return {"total": total, "items": items, "page": page, "per_page": per_page}
