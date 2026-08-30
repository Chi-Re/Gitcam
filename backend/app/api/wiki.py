"""Wiki API：页面树/CRUD/版本历史/回滚"""

import re

from flask import Blueprint, request, g

from app.extensions import db
from app.models import WikiPage
from app.services import wiki as wiki_service, activity
from app.services.notification import create_notification, notify_project_members
from app.utils.decorators import (
    login_required,
    project_from_slug,
    member_role,
    project_visible,
    is_owner_or_admin,
)

bp = Blueprint("wiki", __name__, url_prefix="/api/projects/<string:slug>/wiki")

PATH_RE = re.compile(r"^[\w\u4e00-\u9fa5./-]{1,200}$")


def _check_access(slug, min_role="viewer"):
    project = project_from_slug(slug)
    role = member_role(g.user, project)
    if role is None:
        if project.visibility == "public" and min_role == "viewer":
            return project, "viewer", None, None
        return None, None, "无权访问该项目", 403
    return project, role, None, None


@bp.get("/tree")
@login_required
def page_tree(slug):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    pages = WikiPage.query.filter_by(project_id=project.id).all()
    return {"pages": [p.to_dict(detail=False) for p in pages]}


@bp.get("/pages/<int:page_id>")
@login_required
def get_page(slug, page_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    page = WikiPage.query.filter_by(id=page_id, project_id=project.id).first()
    if page is None:
        return {"error": "页面不存在"}, 404
    return {"page": page.to_dict(detail=True)}


@bp.post("")
@login_required
def create_page(slug):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    if role == "viewer":
        return {"error": "仅项目成员可以编辑 Wiki"}, 403
    data = request.get_json(silent=True) or {}
    path = (data.get("path") or "").strip().strip("/")
    title = (data.get("title") or "").strip()
    if not path or not PATH_RE.match(path):
        return {"error": "页面路径不合法（字母/数字/中文/./-/，最长 200）"}, 400
    if not title:
        return {"error": "请填写页面标题"}, 400
    if WikiPage.query.filter_by(project_id=project.id, path=path).first():
        return {"error": "该路径已有页面"}, 409
    page = WikiPage(
        project_id=project.id,
        path=path,
        title=title,
        content=(data.get("content") or ""),
        editor_id=g.user.id,
        version=1,
    )
    db.session.add(page)
    db.session.flush()
    activity.record_event(
        project.id, g.user.id, "wiki", "created",
        title=f"创建 Wiki 页面：{title}",
        data={"page_id": page.id, "path": path},
    )
    notify_project_members(
        project.id, "wiki",
        title=f"{g.user.full_name} 创建了 Wiki 页面：{title}",
        url=f"/projects/{project.slug}/wiki",
        exclude_user_id=g.user.id,
    )
    db.session.commit()
    return {"page": page.to_dict(detail=True)}, 201


@bp.put("/pages/<int:page_id>")
@login_required
def update_page(slug, page_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    if role == "viewer":
        return {"error": "仅项目成员可以编辑 Wiki"}, 403
    page = WikiPage.query.filter_by(id=page_id, project_id=project.id).first()
    if page is None:
        return {"error": "页面不存在"}, 404
    data = request.get_json(silent=True) or {}
    content = data.get("content")
    if content is None:
        return {"error": "缺少内容"}, 400
    title = (data.get("title") or page.title).strip()
    wiki_service.save_page_edit(page, content, title, g.user.id)
    activity.record_event(
        project.id, g.user.id, "wiki", "updated",
        title=f"更新 Wiki 页面：{page.title}（v{page.version}）",
        data={"page_id": page.id, "path": page.path, "version": page.version},
    )
    notify_project_members(
        project.id, "wiki",
        title=f"{g.user.full_name} 更新了 Wiki 页面：{page.title}（v{page.version}）",
        url=f"/projects/{project.slug}/wiki",
        exclude_user_id=g.user.id,
    )
    db.session.commit()
    return {"page": page.to_dict(detail=True)}


@bp.delete("/pages/<int:page_id>")
@login_required
def delete_page(slug, page_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    page = WikiPage.query.filter_by(id=page_id, project_id=project.id).first()
    if page is None:
        return {"error": "页面不存在"}, 404
    if page.editor_id != g.user.id and not is_owner_or_admin(project, g.user):
        return {"error": "仅页面作者或项目Owner可以删除"}, 403
    activity.record_event(
        project.id, g.user.id, "wiki", "deleted",
        title=f"删除 Wiki 页面：{page.title}",
    )
    db.session.delete(page)
    db.session.commit()
    return {"ok": True}


@bp.get("/pages/<int:page_id>/versions")
@login_required
def page_versions(slug, page_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    page = WikiPage.query.filter_by(id=page_id, project_id=project.id).first()
    if page is None:
        return {"error": "页面不存在"}, 404
    return {"versions": [v.to_dict() for v in page.versions]}


@bp.post("/pages/<int:page_id>/rollback")
@login_required
def rollback(slug, page_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    if role == "viewer":
        return {"error": "仅项目成员可以编辑 Wiki"}, 403
    page = WikiPage.query.filter_by(id=page_id, project_id=project.id).first()
    if page is None:
        return {"error": "页面不存在"}, 404
    data = request.get_json(silent=True) or {}
    try:
        wiki_service.rollback_page(page, int(data.get("version", 0)), g.user.id)
    except ValueError as e:
        return {"error": str(e)}, 400
    activity.record_event(
        project.id, g.user.id, "wiki", "rolled_back",
        title=f"回滚 Wiki 页面：{page.title}（v{page.version}）",
        data={"page_id": page.id, "path": page.path, "version": page.version},
    )
    notify_project_members(
        project.id, "wiki",
        title=f"{g.user.full_name} 回滚了 Wiki 页面：{page.title}（v{page.version}）",
        url=f"/projects/{project.slug}/wiki",
        exclude_user_id=g.user.id,
    )
    db.session.commit()
    return {"page": page.to_dict(detail=True)}
