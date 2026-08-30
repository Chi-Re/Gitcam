from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class WikiPage(db.Model):
    __tablename__ = "wiki_pages"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    path = db.Column(db.String(500), nullable=False)  # 如：guide/start（项目内唯一）
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    editor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    project = db.relationship("Project")
    editor = db.relationship("User")
    versions = db.relationship(
        "WikiVersion", back_populates="page", cascade="all, delete-orphan",
        order_by="WikiVersion.version.desc()", lazy="dynamic",
    )

    __table_args__ = (db.UniqueConstraint("project_id", "path", name="uq_wiki_path"),)

    def to_dict(self, detail=True):
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "path": self.path,
            "title": self.title,
            "version": self.version,
            "editor": self.editor.to_dict(detail=False) if self.editor else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if detail:
            data["content"] = self.content
        return data


class WikiVersion(db.Model):
    __tablename__ = "wiki_versions"

    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey("wiki_pages.id"), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    editor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    page = db.relationship("WikiPage", back_populates="versions")
    editor = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("page_id", "version", name="uq_wiki_version"),)

    def to_dict(self):
        return {
            "id": self.id,
            "page_id": self.page_id,
            "version": self.version,
            "content": self.content,
            "editor": self.editor.to_dict(detail=False) if self.editor else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
