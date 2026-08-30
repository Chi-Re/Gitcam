from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class SiteSetting(db.Model):
    """站点级配置（key-value）"""

    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class AuditLog(db.Model):
    """敏感操作审计日志"""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False, index=True)  # delete_post/ban_user/...
    target_type = db.Column(db.String(32), nullable=True)
    target_id = db.Column(db.String(64), nullable=True)
    detail = db.Column(db.Text, nullable=True)  # JSON 字符串
    ip = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    actor = db.relationship("User", foreign_keys=[actor_id])

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor.username if self.actor else None,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "detail": self.detail,
            "ip": self.ip,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
