from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


POST_CATEGORIES = ("question", "share", "review", "announce", "other")
POST_STATUSES = ("open", "solved", "closed")

CATEGORY_LABELS = {
    "question": "问题求助",
    "share": "经验分享",
    "review": "代码评审",
    "announce": "公告",
    "other": "其他",
}


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
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

    project = db.relationship("Project")
    author = db.relationship("User")
    replies = db.relationship(
        "PostReply",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostReply.created_at",
        lazy="dynamic",
    )
    snippets = db.relationship(
        "CodeSnippet", back_populates="post", cascade="all, delete-orphan", lazy="dynamic"
    )
    discussion_links = db.relationship(
        "DiscussionLink", back_populates="post", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, detail=False, viewer_id=None, my_votes=None):
        data = {
            "id": self.id,
            "project_id": self.project_id,
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
            from app.services.post import render_post_content
            from app.services.discussion import link_context

            data["content_rendered"] = render_post_content(self, viewer_id=viewer_id)
            data["content"] = self.content
            data["snippets"] = [s.to_dict() for s in self.snippets]
            links = [d.to_dict() for d in self.discussion_links]
            for link in links:
                link["context"] = None
                dl = DiscussionLink.query.get(link["id"])
                if dl:
                    link["context"] = link_context(dl)
            data["discussion_links"] = links
            data["replies"] = [r.to_dict(viewer_id=viewer_id) for r in self.replies]
        return data


class PostReply(db.Model):
    __tablename__ = "post_replies"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_accepted = db.Column(db.Boolean, nullable=False, default=False)
    vote_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    post = db.relationship("Post", back_populates="replies")
    author = db.relationship("User")
    snippets = db.relationship(
        "CodeSnippet", back_populates="reply", cascade="all, delete-orphan", lazy="dynamic"
    )
    discussion_links = db.relationship(
        "DiscussionLink", back_populates="reply", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, viewer_id=None):
        from app.services.post import render_post_content
        from app.services.discussion import link_context

        links = [d.to_dict() for d in self.discussion_links]
        for link in links:
            dl = DiscussionLink.query.get(link["id"])
            link["context"] = link_context(dl) if dl else None
        return {
            "id": self.id,
            "post_id": self.post_id,
            "content": self.content,
            "content_rendered": render_post_content(self, viewer_id=viewer_id),
            "is_accepted": self.is_accepted,
            "vote_count": self.vote_count,
            "my_vote": _has_voted(viewer_id, "reply", self.id) if viewer_id else False,
            "author": self.author.to_dict(detail=False) if self.author else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "discussion_links": links,
        }


class PostVote(db.Model):
    __tablename__ = "post_votes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    target_type = db.Column(db.String(8), nullable=False)  # post/reply
    target_id = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_vote_target"),
    )


class CodeSnippet(db.Model):
    """帖子/回帖中从仓库插入的代码片段（正文以 :::snippet:<id>::: 占位符引用）"""

    __tablename__ = "code_snippets"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True, index=True)
    reply_id = db.Column(db.Integer, db.ForeignKey("post_replies.id"), nullable=True, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    file_path = db.Column(db.String(500), nullable=True)  # 来源文件（可为空=手动粘贴）
    language = db.Column(db.String(32), nullable=False, default="plaintext")
    start_line = db.Column(db.Integer, nullable=True)
    end_line = db.Column(db.Integer, nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    post = db.relationship("Post", back_populates="snippets")
    reply = db.relationship("PostReply", back_populates="snippets")

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "reply_id": self.reply_id,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
        }


class DiscussionLink(db.Model):
    """讨论↔代码 绑定（核心表）：帖子/回帖 可绑定 Commit / 文件 / 具体行"""

    __tablename__ = "discussion_links"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)
    reply_id = db.Column(db.Integer, db.ForeignKey("post_replies.id"), nullable=True)
    commit_sha = db.Column(db.String(64), nullable=True, index=True)
    file_path = db.Column(db.String(500), nullable=True)
    line_start = db.Column(db.Integer, nullable=True)
    line_end = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    project = db.relationship("Project")
    post = db.relationship("Post", back_populates="discussion_links")
    reply = db.relationship("PostReply", back_populates="discussion_links")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "post_id": self.post_id,
            "post_title": self.post.title if self.post else None,
            "reply_id": self.reply_id,
            "commit_sha": self.commit_sha,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def _has_voted(user_id, target_type, target_id):
    if not user_id:
        return False
    return PostVote.query.filter_by(
        user_id=user_id, target_type=target_type, target_id=target_id
    ).first() is not None
