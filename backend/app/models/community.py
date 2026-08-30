"""社区论坛（全站板块）模型：独立于项目论坛，代码片段仅引用公共仓库"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.post import POST_CATEGORIES, CATEGORY_LABELS


def utcnow():
    return datetime.now(timezone.utc)


POST_STATUSES = ("open", "solved", "closed")


class CommunityPost(db.Model):
    __tablename__ = "community_posts"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(16), nullable=False, default="other", index=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="open", index=True)
    accepted_reply_id = db.Column(db.Integer, nullable=True)
    vote_count = db.Column(db.Integer, nullable=False, default=0)
    reply_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    author = db.relationship("User")
    replies = db.relationship(
        "CommunityReply", back_populates="post", cascade="all, delete-orphan",
        order_by="CommunityReply.created_at", lazy="dynamic",
    )
    snippets = db.relationship(
        "CommunitySnippet", back_populates="post", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, detail=False, viewer_id=None, my_votes=None):
        data = {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "category_label": CATEGORY_LABELS.get(self.category, self.category),
            "status": self.status,
            "accepted_reply_id": self.accepted_reply_id,
            "vote_count": self.vote_count,
            "reply_count": self.reply_count,
            "author": self.author.to_dict(detail=False) if self.author else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "my_vote": bool(my_votes and self.id in my_votes) if viewer_id else False,
        }
        if detail:
            from app.services.community import render_post_content

            data["content_rendered"] = render_post_content(self)
            data["content"] = self.content
            data["snippets"] = [s.to_dict() for s in self.snippets]
            data["replies"] = [r.to_dict(viewer_id=viewer_id) for r in self.replies]
        return data


class CommunityReply(db.Model):
    __tablename__ = "community_replies"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_accepted = db.Column(db.Boolean, nullable=False, default=False)
    vote_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    post = db.relationship("CommunityPost", back_populates="replies")
    author = db.relationship("User")
    snippets = db.relationship(
        "CommunitySnippet", back_populates="reply", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, viewer_id=None):
        from app.services.community import render_post_content

        return {
            "id": self.id,
            "post_id": self.post_id,
            "content": self.content,
            "content_rendered": render_post_content(self),
            "is_accepted": self.is_accepted,
            "vote_count": self.vote_count,
            "my_vote": _has_voted(viewer_id, "reply", self.id) if viewer_id else False,
            "author": self.author.to_dict(detail=False) if self.author else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CommunityVote(db.Model):
    __tablename__ = "community_votes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    target_type = db.Column(db.String(8), nullable=False)  # post/reply
    target_id = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_community_vote"),
    )


class CommunitySnippet(db.Model):
    """社区帖子中的代码片段（来源必须是公共仓库）"""

    __tablename__ = "community_snippets"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id"), nullable=True, index=True)
    reply_id = db.Column(db.Integer, db.ForeignKey("community_replies.id"), nullable=True, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    file_path = db.Column(db.String(500), nullable=True)
    language = db.Column(db.String(32), nullable=False, default="plaintext")
    start_line = db.Column(db.Integer, nullable=True)
    end_line = db.Column(db.Integer, nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    post = db.relationship("CommunityPost", back_populates="snippets")
    reply = db.relationship("CommunityReply", back_populates="snippets")
    project = db.relationship("Project")

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "reply_id": self.reply_id,
            "project_id": self.project_id,
            "project_slug": self.project.slug if self.project else None,
            "project_name": self.project.name if self.project else None,
            "file_path": self.file_path,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
        }


def _has_voted(user_id, target_type, target_id):
    if not user_id:
        return False
    return CommunityVote.query.filter_by(
        user_id=user_id, target_type=target_type, target_id=target_id
    ).first() is not None
