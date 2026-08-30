from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


PROJECT_TEMPLATES = {
    "course": {
        "name": "课程作业模板",
        "description": "用于课程作业项目，内置课程信息与作业说明文档",
        "readme": """# 课程作业

## 课程信息
- 课程名称：
- 授课教师：
- 学期：

## 作业说明
（在此填写作业要求）

## 提交要求
- 代码需包含必要的注释
- 提交信息请说明完成内容
""",
        "init_files": {"README.md": None},
    },
    "graduation": {
        "name": "毕业设计模板",
        "description": "用于毕业设计项目，内置论文/源码/文档目录结构",
        "readme": """# 毕业设计

## 题目
（填写毕设题目）

## 目录结构
- `src/` 源码
- `docs/` 设计文档
- `thesis/` 论文

## 进度计划
（填写各阶段安排）
""",
        "init_files": {"README.md": None, "src/": None, "docs/": None, "thesis/": None},
    },
    "innovation": {
        "name": "创新创业项目模板",
        "description": "用于创新创业/竞赛项目，内置商业计划与开发计划结构",
        "readme": """# 创新创业项目

## 项目简介
（一句话说明项目）

## 创新点
- 

## 商业模式
（说明盈利方式）

## 团队分工
（填写成员分工）
""",
        "init_files": {"README.md": None, "docs/business-plan.md": None},
    },
    "interest": {
        "name": "兴趣小组模板",
        "description": "用于兴趣小组/开源项目，内置社区协作约定",
        "readme": """# 兴趣小组项目

## 项目简介
（说明项目用途）

## 贡献指南
1. 先创建 Issue 说明要解决的问题
2. Fork 本项目并创建分支
3. 提交 PR 时关联对应 Issue

## 成员
（填写成员列表）
""",
        "init_files": {"README.md": None, "CONTRIBUTING.md": None, "LICENSE": None},
    },
    "blank": {
        "name": "空项目",
        "description": "空白仓库，一切从零开始",
        "readme": """# 项目名称

（项目简介）
""",
        "init_files": {"README.md": None},
    },
}


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.String(500), nullable=True)
    visibility = db.Column(db.String(16), nullable=False, default="private")  # public/private
    template_type = db.Column(db.String(16), nullable=False, default="blank")
    default_branch = db.Column(db.String(64), nullable=False, default="main")
    language = db.Column(db.String(32), nullable=True)
    tags = db.Column(db.String(255), nullable=True)  # 逗号分隔
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    owner = db.relationship("User", foreign_keys=[owner_id])
    members = db.relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan", lazy="dynamic"
    )

    def tag_list(self):
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

    def repo_path(self):
        import os
        from flask import current_app
        return os.path.join(current_app.config["REPO_ROOT"], f"{self.id}.git")

    def git_url(self, kind="http"):
        from flask import current_app
        base = current_app.config["EXTERNAL_BASE_URL"].rstrip("/")
        return f"{base}/git/{self.slug}.git"

    def to_dict(self, include_members=False):
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "visibility": self.visibility,
            "template_type": self.template_type,
            "template_name": PROJECT_TEMPLATES.get(self.template_type, {}).get("name", ""),
            "default_branch": self.default_branch,
            "language": self.language,
            "tags": self.tag_list(),
            "owner": self.owner.to_dict(detail=False) if self.owner else None,
            "owner_id": self.owner_id,
            "git_url": self.git_url(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "member_count": self.members.count(),
        }
        if include_members:
            data["members"] = [m.to_dict() for m in self.members]
        return data


class ProjectMember(db.Model):
    __tablename__ = "project_members"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(16), nullable=False, default="developer")  # owner/developer/viewer
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    project = db.relationship("Project", back_populates="members")
    user = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username,
            "full_name": self.user.full_name,
            "avatar_url": self.user.avatar_url,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
