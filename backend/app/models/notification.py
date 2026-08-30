from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Notification(db.Model):
    """站内通知收件箱"""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(32), nullable=False)  # comment/mention/issue/repo/wiki
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    project_id = db.Column(db.Integer, nullable=True)
    url = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    email_sent = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "project_id": self.project_id,
            "url": self.url,
            "is_read": self.is_read,
            "email_sent": self.email_sent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NotificationPref(db.Model):
    """用户通知偏好配置"""

    __tablename__ = "notification_prefs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    comment = db.Column(db.Boolean, nullable=False, default=True)
    mention = db.Column(db.Boolean, nullable=False, default=True)
    issue = db.Column(db.Boolean, nullable=False, default=True)
    repo = db.Column(db.Boolean, nullable=False, default=True)
    wiki = db.Column(db.Boolean, nullable=False, default=True)
    email_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_digest = db.Column(db.String(16), nullable=False, default="immediate")  # immediate/daily
