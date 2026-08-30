"""权限工具：系统角色 RBAC + 项目成员角色"""

from functools import wraps

from flask import g, abort
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.models import User, ProjectMember, Project

PROJECT_ROLE_LEVEL = {"viewer": 1, "developer": 2, "owner": 3}


def load_current_user():
    """从 JWT 加载当前用户到 g.user；返回 None 表示未认证"""
    verify_jwt_in_request(optional=True)
    identity = get_jwt_identity()
    if identity is None:
        g.user = None
        return None
    user = User.query.get(identity)
    if user and not user.is_active:
        g.user = None
        return None
    g.user = user
    return user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = load_current_user()
        if user is None:
            abort(401, description="未登录或登录已过期")
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    """系统角色校验：student/teacher/admin"""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = load_current_user()
            if user is None:
                abort(401, description="未登录或登录已过期")
            if user.role not in roles:
                abort(403, description="权限不足")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def project_from_slug(slug):
    project = Project.query.filter_by(slug=slug).first()
    if project is None:
        abort(404, description="项目不存在")
    g.project = project
    return project


def member_role(user, project):
    if user is None:
        return None
    if user.role == "admin":
        return "owner"
    if project.owner_id == user.id:
        return "owner"
    member = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
    return member.role if member else None


def project_visible(project, role):
    """公开项目所有人可见；私有项目需为成员"""
    return project.visibility == "public" or role is not None


def project_access_required(min_role="viewer"):
    """项目访问校验：需为项目成员（或公开项目 + viewer 只读）"""
    from flask import request

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = load_current_user()
            if user is None:
                abort(401, description="未登录或登录已过期")
            slug = kwargs.get("slug") or request.view_args.get("slug")
            project = project_from_slug(slug)
            role = member_role(user, project)
            if role is None:
                # 公开项目：登录用户可只读访问
                if project.visibility == "public" and min_role == "viewer":
                    g.project_role = "viewer"
                    return fn(*args, **kwargs)
                abort(403, description="无权访问该项目")
            if PROJECT_ROLE_LEVEL.get(role, 0) < PROJECT_ROLE_LEVEL.get(min_role, 1):
                abort(403, description="权限不足")
            g.project_role = role
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def is_owner_or_admin(project, user):
    if user is None:
        return False
    return user.role == "admin" or project.owner_id == user.id
