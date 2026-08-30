"""回复历史记录表：用户回帖快照（帖子删除后仍保留，用于展示“已删除”）"""

from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class UserReplyRecord(db.Model):
    __tablename__ = "user_reply_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    scope = db.Column(db.String(16), nullable=False, default="project")  # project/community
    project_id = db.Column(db.Integer, nullable=True)
    project_slug = db.Column(db.String(80), nullable=True)
    post_id = db.Column(db.Integer, nullable=False, index=True)
    post_title = db.Column(db.String(255), nullable=False)
    reply_id = db.Column(db.Integer, nullable=False)
    content_snippet = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    def to_dict(self, post_exists=True):
        return {
            "id": self.id,
            "scope": self.scope,
            "project_id": self.project_id,
            "project_slug": self.project_slug,
            "post_id": self.post_id,
            "post_title": self.post_title,
            "reply_id": self.reply_id,
            "content_snippet": self.content_snippet,
            "post_exists": post_exists,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
