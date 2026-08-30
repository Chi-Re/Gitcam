"""讨论绑定查询 API：按 Commit / 文件 查询（供仓库页与提交详情页使用）"""

from flask import Blueprint, request

from app.models import DiscussionLink
from app.services import discussion as discussion_service
from app.utils.decorators import (
    login_required,
    project_from_slug,
    member_role,
    project_visible,
)

bp = Blueprint("discussion", __name__, url_prefix="/api/projects/<string:slug>/discussion-links")


def _check_access(slug):
    project = project_from_slug(slug)
    if not project_visible(project, member_role(__import__("flask").g.user, project)):
        return None, "无权访问该项目", 403
    return project, None, None


@bp.get("")
@login_required
def query_links(slug):
    from flask import g

    project, error, code = _check_access(slug)
    if error:
        return {"error": error}, code

    commit_sha = (request.args.get("commit_sha") or "").strip() or None
    file_path = (request.args.get("file_path") or "").strip() or None
    if commit_sha and file_path:
        links = discussion_service.query_file_commit_links(project.id, commit_sha, file_path)
    elif commit_sha:
        links = discussion_service.query_by_commit(project.id, commit_sha)
    elif file_path:
        links = discussion_service.query_by_file(project.id, file_path)
    else:
        return {"error": "缺少 commit_sha 或 file_path 参数"}, 400

    # 公开项目也需登录即可见；私有项目需成员（_check_access 已校验）
    items = []
    for l in links:
        item = discussion_service.post_with_context(l)
        items.append(item)
    return {"items": items}
