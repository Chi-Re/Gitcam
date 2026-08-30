from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    student_id = db.Column(db.String(32), unique=True, nullable=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(16), nullable=False, default="student")  # student/teacher/admin
    college = db.Column(db.String(128), nullable=True)
    major_class = db.Column(db.String(128), nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    gitee_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    @property
    def password(self):
        raise AttributeError("password is not readable")

    @password.setter
    def password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_password(self, value):
        return check_password_hash(self.password_hash, value)

    def to_dict(self, detail=True):
        data = {
            "id": self.id,
            "email": self.email,
            "student_id": self.student_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "college": self.college,
            "major_class": self.major_class,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "github_url": self.github_url,
            "gitee_url": self.gitee_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        return data


class UserLoginLog(db.Model):
    """登录日志（管理员审计用）"""

    __tablename__ = "user_login_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    success = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


@event.listens_for(User.__table__, "after_create")
def _add_admin(mapper, connection, **kwargs):
    with db.session() as session:
        if not session.query(User).filter_by(username="admin").first():
            admin = User(
                email="admin@gitcam.local",
                username="admin",
                full_name="系统管理员",
                role="admin",
                college="系统管理",
            )
            admin.password = "admin123"
            session.add(admin)
            session.commit()
