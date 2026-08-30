"""通知服务：创建站内通知 + 按偏好发送邮件"""

from flask import g

from app.extensions import db
from app.models.notification import Notification, NotificationPref
from app.models.admin import SiteSetting


def _global_enabled():
    """站点通知总开关（管理员配置）"""
    setting = SiteSetting.query.filter_by(key="notifications_enabled").first()
    if setting is None:
        return True
    return setting.value != "false"


def create_notification(user_id, type_, title, content=None, project_id=None, url=None, send_email=True):
    """创建站内通知；send_email 时按用户偏好尝试发邮件（失败静默降级）"""
    if not _global_enabled():
        return None
    pref = NotificationPref.query.filter_by(user_id=user_id).first()
    if pref and not getattr(pref, type_, True):
        return None

    notification = Notification(
        user_id=user_id,
        type=type_,
        title=title,
        content=content,
        project_id=project_id,
        url=url,
    )
    db.session.add(notification)
    db.session.flush()

    if send_email:
        from app.services.mail import send_notification_email

        try:
            send_notification_email(notification)
        except Exception:
            db.session.rollback()
            db.session.add(notification)
            db.session.flush()
    return notification


def notify_project_members(project_id, type_, title, content=None, url=None, exclude_user_id=None,
                           role_filter=None):
    """批量通知项目成员（按成员偏好过滤）；返回通知数"""
    from app.models import ProjectMember, User

    if not _global_enabled():
        return 0
    query = ProjectMember.query.filter_by(project_id=project_id)
    members = query.all()
    count = 0
    for m in members:
        if exclude_user_id and m.user_id == exclude_user_id:
            continue
        if role_filter and m.role not in role_filter:
            continue
        user = User.query.get(m.user_id)
        if not user or not user.is_active:
            continue
        pref = NotificationPref.query.filter_by(user_id=m.user_id).first()
        if pref and not getattr(pref, type_, True):
            continue
        n = create_notification(
            user_id=m.user_id, type_=type_, title=title, content=content,
            project_id=project_id, url=url, send_email=False,
        )
        if n:
            count += 1
    return count


def get_pref_or_create(user_id):
    pref = NotificationPref.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = NotificationPref(user_id=user_id)
        db.session.add(pref)
        db.session.commit()
    return pref


def mark_all_read(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
