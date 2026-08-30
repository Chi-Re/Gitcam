"""项目管理：创建(模板)/详情/搜索/成员管理/动态流"""

import re

from flask import Blueprint, request, g
from sqlalchemy import or_

from app.extensions import db
from app.models import (
    User,
    Project,
    ProjectMember,
    PROJECT_TEMPLATES,
    ActivityEvent,
)
from app.services.git_service import GitService, GitServiceError, DEFAULT_BRANCH
from app.services import activity
from app.utils.decorators import (
    login_required,
    project_from_slug,
    member_role,
    is_owner_or_admin,
    project_visible,
)

bp = Blueprint("projects", __name__, url_prefix="/api/projects")

SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,63}$")


@bp.get("/templates")
def templates():
    return {"templates": [
        {
            "type": key,
            "name": value["name"],
            "description": value["description"],
            "files": list(value["init_files"].keys()),
        }
        for key, value in PROJECT_TEMPLATES.items()
    ]}


@bp.get("")
@login_required
def list_projects():
    q = request.args.get("q") or ""
    tag = request.args.get("tag") or ""
    language = request.args.get("language") or ""
    visibility = request.args.get("visibility") or ""
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)

    # 可访问的项目：公开项目 + 我参与的项目
    my_ids = [m.project_id for m in ProjectMember.query.filter_by(user_id=g.user.id).all()]
    my_ids.append(g.user.id)
    own_ids = [p.id for p in Project.query.filter_by(owner_id=g.user.id).all()]
    accessible = set(my_ids) | set(own_ids)

    query = Project.query.filter(
        or_(
            Project.visibility == "public",
            Project.id.in_(accessible),
        )
    )
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Project.name.like(like),
                Project.description.like(like),
                Project.tags.like(like),
            )
        )
    if tag:
        query = query.filter(Project.tags.like(f"%{tag}%"))
    if language:
        query = query.filter_by(language=language)
    if visibility and visibility in ("public", "private"):
        query = query.filter_by(visibility=visibility)

    total = query.count()
    projects = (
        query.order_by(Project.updated_at.desc(), Project.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "total": total,
        "items": [p.to_dict() for p in projects],
        "page": page,
        "per_page": per_page,
    }


@bp.post("")
@login_required
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return {"error": "请填写项目名称"}, 400
    slug = (data.get("slug") or "").strip()
    if not slug:
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.lower()).strip("-") or name.lower()
    if not SLUG_RE.match(slug):
        return {"error": "项目标识需为 2-64 位字母/数字/._-，且不能以 ._- 开头"}, 400
    if Project.query.filter_by(slug=slug).first():
        return {"error": "项目标识已存在，请更换"}, 409
    template_type = data.get("template_type") or "blank"
    if template_type not in PROJECT_TEMPLATES:
        return {"error": "模板类型不存在"}, 400
    visibility = data.get("visibility") or "private"
    if visibility not in ("public", "private"):
        return {"error": "可见性只能是 public/private"}, 400

    project = Project(
        name=name,
        slug=slug,
        description=(data.get("description") or "").strip() or None,
        visibility=visibility,
        template_type=template_type,
        default_branch=DEFAULT_BRANCH,
        language=(data.get("language") or "").strip() or None,
        tags=",".join([t.strip() for t in (data.get("tags") or []) if t.strip()]) or None,
        owner_id=g.user.id,
    )
    db.session.add(project)
    db.session.flush()

    owner_member = ProjectMember(project_id=project.id, user_id=g.user.id, role="owner")
    db.session.add(owner_member)

    # 初始化 Git 裸仓库 + 模板初始提交
    try:
        repo = GitService.create_bare(project.id, DEFAULT_BRANCH)
        template = PROJECT_TEMPLATES[template_type]
        readme_content = template["readme"].replace("# 项目名称", f"# {name}")
        files = {}
        for f in template["init_files"]:
            if f.endswith("/"):
                files[f.rstrip("/") + "/.gitkeep"] = ""
            else:
                files[f] = readme_content if f == "README.md" else ""
        sha = repo.ensure_initial_commit(
            files,
            f"初始化项目：{name}",
            author_name=g.user.full_name,
            author_email=g.user.email,
        )
        if sha:
            db.session.add(
                ActivityEvent(
                    project_id=project.id,
                    actor_id=g.user.id,
                    event_type="commit",
                    action="created",
                    title="初始化项目：{}".format(name),
                    commit_sha=sha,
                )
            )
    except GitServiceError as e:
        db.session.rollback()
        return {"error": f"仓库初始化失败: {e}"}, 500

    db.session.add(
        ActivityEvent(
            project_id=project.id,
            actor_id=g.user.id,
            event_type="project",
            action="created",
            title=f"创建项目 {name}",
            data={"template": template_type, "visibility": visibility},
        )
    )
    db.session.commit()
    return {"project": project.to_dict(include_members=True)}, 201


@bp.get("/<string:slug>")
@login_required
def get_project(slug):
    project = project_from_slug(slug)
    role = member_role(g.user, project)
    if not project_visible(project, role):
        return {"error": "无权访问该项目"}, 403
    data = project.to_dict(include_members=True)
    data["my_role"] = role
    data["repo_size"] = None
    if GitService.exists(project.id):
        try:
            repo = GitService.open(project.id)
            data["repo_size"] = repo.repo_size()
            data["commit_count"] = repo.total_commits()
        except GitServiceError:
            pass
    return {"project": data}


@bp.put("/<string:slug>")
@login_required
def update_project(slug):
    project = project_from_slug(slug)
    if not is_owner_or_admin(project, g.user):
        return {"error": "仅项目拥有者可以修改项目信息"}, 403
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"]:
        project.name = (data["name"] or "").strip()
    if "description" in data:
        project.description = (data["description"] or "").strip() or None
    if "visibility" in data and data["visibility"] in ("public", "private"):
        project.visibility = data["visibility"]
    if "language" in data:
        project.language = (data["language"] or "").strip() or None
    if "tags" in data:
        project.tags = ",".join([t.strip() for t in data["tags"] if t.strip()]) or None
    db.session.commit()
    return {"project": project.to_dict(include_members=True)}


@bp.delete("/<string:slug>")
@login_required
def delete_project(slug):
    project = project_from_slug(slug)
    if not is_owner_or_admin(project, g.user):
        return {"error": "仅项目拥有者可以删除项目"}, 403
    import os
    from flask import current_app

    repo_path = os.path.join(current_app.config["REPO_ROOT"], f"{project.id}.git")
    if os.path.isdir(repo_path):
        import shutil
        shutil.rmtree(repo_path)
    ActivityEvent.query.filter_by(project_id=project.id).delete()
    ProjectMember.query.filter_by(project_id=project.id).delete()
    from app.services import audit

    audit.record("delete_project", "project", project.id, {"slug": project.slug, "name": project.name})
    db.session.delete(project)
    db.session.commit()
    return {"ok": True}


# ---------- 成员管理 ----------

@bp.get("/<string:slug>/members")
@login_required
def list_members(slug):
    project = project_from_slug(slug)
    if not project_visible(project, member_role(g.user, project)):
        return {"error": "无权访问该项目"}, 403
    return {"members": [m.to_dict() for m in project.members]}


@bp.post("/<string:slug>/members")
@login_required
def add_member(slug):
    project = project_from_slug(slug)
    if not is_owner_or_admin(project, g.user):
        return {"error": "仅项目拥有者可以添加成员"}, 403
    data = request.get_json(silent=True) or {}
    user = None
    account = (data.get("account") or "").strip()
    if not account:
        return {"error": "请提供成员账号（用户名/邮箱/学号）"}, 400
    if "@" in account:
        user = User.query.filter_by(email=account.lower()).first()
    if user is None:
        user = User.query.filter_by(username=account).first()
    if user is None and account.isdigit():
        user = User.query.filter_by(student_id=account).first()
    if user is None:
        return {"error": "用户不存在"}, 404
    if ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first():
        return {"error": "该用户已是项目成员"}, 409
    role = data.get("role") or "developer"
    if role not in ("developer", "viewer", "owner"):
        return {"error": "角色只能是 owner/developer/viewer"}, 400

    db.session.add(ProjectMember(project_id=project.id, user_id=user.id, role=role))
    activity.record_event(
        project.id, g.user.id, "member", "added",
        title=f"添加成员 {user.full_name}",
        data={"user_id": user.id, "username": user.username, "role": role},
    )
    db.session.commit()
    return {"members": [m.to_dict() for m in project.members]}, 201


@bp.put("/<string:slug>/members/<int:user_id>")
@login_required
def update_member_role(slug, user_id):
    project = project_from_slug(slug)
    if not is_owner_or_admin(project, g.user):
        return {"error": "仅项目拥有者可以修改成员角色"}, 403
    member = ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first()
    if member is None:
        return {"error": "该用户不是项目成员"}, 404
    if member.role == "owner":
        return {"error": "不能修改拥有者角色"}, 400
    data = request.get_json(silent=True) or {}
    role = data.get("role")
    if role not in ("developer", "viewer"):
        return {"error": "角色只能是 developer/viewer"}, 400
    member.role = role
    activity.record_event(
        project.id, g.user.id, "member", "updated",
        title=f"调整成员 {member.user.full_name} 角色为 {role}",
        data={"user_id": user_id, "role": role},
    )
    db.session.commit()
    return {"members": [m.to_dict() for m in project.members]}


@bp.delete("/<string:slug>/members/<int:user_id>")
@login_required
def remove_member(slug, user_id):
    project = project_from_slug(slug)
    if not is_owner_or_admin(project, g.user):
        return {"error": "仅项目拥有者可以移除成员"}, 403
    member = ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first()
    if member is None:
        return {"error": "该用户不是项目成员"}, 404
    if member.role == "owner":
        return {"error": "不能移除项目拥有者"}, 400
    db.session.delete(member)
    activity.record_event(
        project.id, g.user.id, "member", "removed",
        title=f"移除成员 {member.user.full_name}",
        data={"user_id": user_id},
    )
    db.session.commit()
    return {"members": [m.to_dict() for m in project.members]}


# ---------- 动态流 ----------

@bp.get("/<string:slug>/activities")
@login_required
def project_activities(slug):
    project = project_from_slug(slug)
    if not project_visible(project, member_role(g.user, project)):
        return {"error": "无权访问该项目"}, 403
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 30)), 1), 100)
    event_type = request.args.get("type", "all")
    result = activity.query_events(project.id, event_type, page, per_page)
    return result
