"""邮件通知服务：SMTP 可配置，未配置或发送失败时静默降级（不影响站内通知）"""

import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.header import Header

from flask import current_app

logger = logging.getLogger(__name__)

_mail_lock = threading.Lock()


def _smtp_configured():
    cfg = current_app.config
    return cfg.get("MAIL_ENABLED") and cfg.get("MAIL_SMTP_HOST") and cfg.get("MAIL_SMTP_USER")


def send_mail(to_address, subject, html_body):
    """发送邮件；未配置 SMTP 时返回 False"""
    cfg = current_app.config
    if not _smtp_configured():
        logger.debug("SMTP 未配置，邮件跳过: %s", subject)
        return False
    try:
        msg = MIMEText(html_body, "html", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = cfg["MAIL_FROM"]
        msg["To"] = to_address
        with _mail_lock:
            if cfg.get("MAIL_USE_SSL"):
                server = smtplib.SMTP_SSL(cfg["MAIL_SMTP_HOST"], cfg["MAIL_SMTP_PORT"], timeout=15)
            else:
                server = smtplib.SMTP(cfg["MAIL_SMTP_HOST"], cfg["MAIL_SMTP_PORT"], timeout=15)
                server.starttls()
            try:
                server.login(cfg["MAIL_SMTP_USER"], cfg["MAIL_SMTP_PASSWORD"])
                server.sendmail(cfg["MAIL_FROM"], [to_address], msg.as_string())
            finally:
                server.quit()
        logger.info("邮件已发送至 %s: %s", to_address, subject)
        return True
    except Exception as e:
        logger.warning("邮件发送失败（已降级为仅站内通知）: %s", e)
        return False


def send_notification_email(notification):
    """根据用户通知偏好发送通知邮件（站内通知已落库后调用）"""
    from app.models.notification import NotificationPref, Notification

    pref = NotificationPref.query.filter_by(user_id=notification.user_id).first()
    if pref and not pref.email_enabled:
        return False
    user = notification.__table__.metadata.tables  # noqa
    from app.models import User

    user = User.query.get(notification.user_id)
    if not user or not user.email:
        return False
    ok = send_mail(
        user.email,
        notification.title,
        f"<p>{notification.title}</p><p>{notification.content or ''}</p>"
        + (f'<p><a href="{notification.url}">查看详情</a></p>' if notification.url else ""),
    )
    if ok:
        notification.email_sent = True
        from app.extensions import db

        db.session.commit()
    return ok
