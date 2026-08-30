from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


ISSUE_STATUSES = ("open", "in_progress", "resolved", "closed")
ISSUE_PRIORITIES = ("low", "medium", "high", "urgent")

STATUS_LABELS = {
    "open": "待处理",
    "in_progress": "处理中",
    "resolved": "已解决",
    "closed": "已关闭",
}
PRIORITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "urgent": "紧急",
}


class Issue(db.Model):
    __tablename__ = "issues"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(16), nullable=False, default="open", index=True)
    priority = db.Column(db.String(16), nullable=False, default="medium", index=True)
    labels = db.Column(db.String(255), nullable=True)  # 逗号分隔
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    milestone = db.Column(db.String(128), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    comment_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    closed_at = db.Column(db.DateTime, nullable=True)

    project = db.relationship("Project")
    assignee = db.relationship("User", foreign_keys=[assignee_id])
    creator = db.relationship("User", foreign_keys=[created_by])
    comments = db.relationship(
        "IssueComment", back_populates="issue", cascade="all, delete-orphan",
        order_by="IssueComment.created_at", lazy="dynamic",
    )
    commits = db.relationship(
        "IssueCommit", back_populates="issue", cascade="all, delete-orphan",
        order_by="IssueCommit.created_at.desc()", lazy="dynamic",
    )

    def label_list(self):
        return [l.strip() for l in (self.labels or "").split(",") if l.strip()]

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "number": self.id,
            "title": self.title,
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, self.status),
            "priority": self.priority,
            "priority_label": PRIORITY_LABELS.get(self.priority, self.priority),
            "labels": self.label_list(),
            "assignee": self.assignee.to_dict(detail=False) if self.assignee else None,
            "milestone": self.milestone,
            "creator": self.creator.to_dict(detail=False) if self.creator else None,
            "comment_count": self.comment_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }
        if detail:
            data["description"] = self.description
            data["comments"] = [c.to_dict() for c in self.comments]
            data["commits"] = [c.to_dict() for c in self.commits]
        return data


class IssueComment(db.Model):
    __tablename__ = "issue_comments"

    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    issue = db.relationship("Issue", back_populates="comments")
    author = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "content": self.content,
            "author": self.author.to_dict(detail=False) if self.author else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class IssueCommit(db.Model):
    """Issue ↔ Commit 关联（提交信息含 fix #N 自动生成）"""

    __tablename__ = "issue_commits"

    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id"), nullable=False, index=True)
    commit_sha = db.Column(db.String(64), nullable=False, index=True)
    linked_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    issue = db.relationship("Issue", back_populates="commits")
    linker = db.relationship("User", foreign_keys=[linked_by])

    __table_args__ = (db.UniqueConstraint("issue_id", "commit_sha", name="uq_issue_commit"),)

    def to_dict(self):
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "commit_sha": self.commit_sha,
            "linked_by": self.linker.username if self.linker else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
