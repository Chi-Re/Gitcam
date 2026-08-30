"""用户 API：公开资料 / 通知中心 / 通知偏好"""

from flask import Blueprint, request, g
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models import User, Notification
from app.services.notification import get_pref_or_create, mark_all_read
from app.utils.decorators import login_required

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.get("/<string:username>")
def public_profile(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return {"error": "用户不存在"}, 404
    return {"user": user.to_dict()}


@bp.get("/me/notifications")
@login_required
def my_notifications():
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    q = Notification.query.filter_by(user_id=g.user.id)
    if request.args.get("unread") == "1":
        q = q.filter_by(is_read=False)
    total = q.count()
    items = q.order_by(Notification.created_at.desc(), Notification.id.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    unread = Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
    return {
        "total": total,
        "unread": unread,
        "items": [n.to_dict() for n in items],
    }


@bp.post("/me/notifications/read")
@login_required
def read_notification():
    data = request.get_json(silent=True) or {}
    if data.get("all"):
        mark_all_read(g.user.id)
        return {"ok": True}
    nid = data.get("id")
    if nid:
        n = Notification.query.filter_by(id=nid, user_id=g.user.id).first()
        if n:
            n.is_read = True
            db.session.commit()
    return {"ok": True}


@bp.get("/me/reply-history")
@login_required
def my_reply_history():
    from app.models import UserReplyRecord, Post, CommunityPost

    scope = request.args.get("scope", "all")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    q = UserReplyRecord.query.filter_by(user_id=g.user.id)
    if scope and scope in ("project", "community"):
        q = q.filter_by(scope=scope)
    total = q.count()
    records = (
        q.order_by(UserReplyRecord.created_at.desc(), UserReplyRecord.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    items = []
    for r in records:
        exists = False
        if r.scope == "community":
            exists = CommunityPost.query.get(r.post_id) is not None
        else:
            exists = Post.query.get(r.post_id) is not None
        items.append(r.to_dict(post_exists=exists))
    return {"total": total, "items": items, "page": page, "per_page": per_page}


@bp.delete("/me/notifications/<int:notification_id>")
@login_required
def delete_notification(notification_id):
    n = Notification.query.filter_by(id=notification_id, user_id=g.user.id).first()
    if n is None:
        return {"error": "通知不存在"}, 404
    db.session.delete(n)
    db.session.commit()
    return {"ok": True}


@bp.delete("/me/notifications")
@login_required
def clear_notifications():
    Notification.query.filter_by(user_id=g.user.id).delete()
    db.session.commit()
    return {"ok": True}


@bp.get("/me/notification-prefs")
@login_required
def get_prefs():
    pref = get_pref_or_create(g.user.id)
    return {"prefs": {
        "comment": pref.comment,
        "mention": pref.mention,
        "issue": pref.issue,
        "repo": pref.repo,
        "wiki": pref.wiki,
        "email_enabled": pref.email_enabled,
        "email_digest": pref.email_digest,
    }}


@bp.put("/me/notification-prefs")
@login_required
def update_prefs():
    data = request.get_json(silent=True) or {}
    pref = get_pref_or_create(g.user.id)
    for field in ("comment", "mention", "issue", "repo", "wiki", "email_enabled"):
        if field in data:
            setattr(pref, field, bool(data[field]))
    if "email_digest" in data and data["email_digest"] in ("immediate", "daily"):
        pref.email_digest = data["email_digest"]
    db.session.commit()
    return {"ok": True}
