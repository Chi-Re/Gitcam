from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ActivityEvent(db.Model):
    """项目动态聚合流事件"""

    __tablename__ = "activity_events"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    event_type = db.Column(db.String(32), nullable=False)  # commit/member/issue/post/wiki/...
    action = db.Column(db.String(32), nullable=False, default="created")
    title = db.Column(db.String(255), nullable=True)
    ref_type = db.Column(db.String(16), nullable=True)  # branch/tag/...
    ref_name = db.Column(db.String(64), nullable=True)
    commit_sha = db.Column(db.String(64), nullable=True)
    data = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    project = db.relationship("Project")
    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "event_type": self.event_type,
            "action": self.action,
            "title": self.title,
            "ref_type": self.ref_type,
            "ref_name": self.ref_name,
            "commit_sha": self.commit_sha,
            "data": self.data,
            "actor": self.actor.to_dict(detail=False) if self.actor else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
