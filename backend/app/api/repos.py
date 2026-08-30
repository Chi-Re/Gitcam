"""仓库 API：文件浏览 / 提交历史 / Diff / 分支标签"""

import os

from flask import Blueprint, request, g, current_app

from app.models import Project
from app.services.git_service import GitService, GitServiceError
from app.utils.decorators import (
    login_required,
    project_from_slug,
    member_role,
    project_visible,
)

bp = Blueprint("repos", __name__, url_prefix="/api/projects/<string:slug>/repo")


def _check_access(slug):
    project = project_from_slug(slug)
    if not project_visible(project, member_role(g.user, project)):
        return None, "无权访问该项目", 403
    if not GitService.exists(project.id):
        return None, "仓库尚未初始化", 404
    try:
        return GitService.open(project.id), None, None
    except GitServiceError as e:
        return None, str(e), 404


@bp.get("/tree-index")
@login_required
def tree_index(slug):
    """完整目录树索引：全部条目路径 + 目录/文件统计（供 Go to file 搜索与树底统计）"""
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    branch = request.args.get("branch")
    try:
        rev = branch or repo.default_branch()
        out = repo.repo.git.ls_tree("-r", "--full-name", rev)
    except Exception as e:
        return {"error": str(e)}, 404

    dirs = set()
    files = 0
    paths = []
    truncated = False
    MAX_INDEX = 20000
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        path = parts[1]
        files += 1
        # 从文件路径推导目录（ls-tree -r 不输出目录条目）
        segments = path.split("/")
        for i in range(1, len(segments)):
            dirs.add("/".join(segments[:i]))
        paths.append(path)
    if files > MAX_INDEX:
        truncated = True
        paths = paths[:MAX_INDEX]
    return {
        "paths": paths,
        "dirCount": len(dirs),
        "fileCount": files,
        "truncated": truncated,
    }, {"Cache-Control": "private, max-age=60"}


@bp.get("/tree")
@login_required
def file_tree(slug):
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    path = request.args.get("path", "")
    branch = request.args.get("branch")
    try:
        entries = repo.file_tree(branch=branch, path=path)
    except GitServiceError as e:
        return {"error": str(e)}, 404
    return {
        "path": path.strip("/"),
        "entries": entries,
        "branch": branch or repo.default_branch(),
        "readme": _find_readme(entries, path),
    }, {"Cache-Control": "private, max-age=30"}


def _find_readme(entries, path):
    for e in entries:
        if e["type"] == "blob" and e["name"].lower().startswith("readme"):
            return f"{path}/{e['name']}".strip("/") if path else e["name"]
    return None


@bp.get("/raw")
@login_required
def raw_file(slug):
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    path = request.args.get("path", "")
    branch = request.args.get("branch")
    ref = request.args.get("ref")
    try:
        blob = repo._resolve_commit(branch, ref).tree / path.strip("/")
        if blob.type != "blob":
            return {"error": "路径不是文件"}, 404
    except Exception:
        return {"error": "路径不存在"}, 404

    def generate():
        stream = blob.data_stream
        try:
            while True:
                chunk = stream.read(1024 * 64)
                if not chunk:
                    break
                yield chunk
        finally:
            stream.close()

    resp = current_app.response_class(generate(), mimetype="application/octet-stream")
    resp.headers["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
    resp.headers["Cache-Control"] = "private, max-age=60"
    resp.headers["Content-Length"] = str(blob.size)
    return resp


@bp.get("/blob")
@login_required
def blob_info(slug):
    """文件内容（文本截断保护）与元信息"""
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    path = request.args.get("path", "")
    branch = request.args.get("branch")
    ref = request.args.get("ref")
    try:
        data, size = repo.blob_content(path, branch=branch, ref=ref)
    except GitServiceError as e:
        return {"error": str(e)}, 404
    max_size = 1024 * 1024  # 1MB 以上不再返回文本内容
    return {
        "path": path.strip("/"),
        "size": size,
        "truncated": size > max_size,
        "content": data.decode("utf-8", errors="replace") if size <= max_size else "",
    }, {"Cache-Control": "private, max-age=30"}


@bp.get("/commits")
@login_required
def commit_log(slug):
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    branch = request.args.get("branch")
    path = request.args.get("path")
    keyword = request.args.get("q")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 50)), 1), 100)
    try:
        commits = repo.commit_log(branch=branch, path=path, page=page, per_page=per_page, keyword=keyword)
    except GitServiceError as e:
        return {"error": str(e)}, 404
    return {
        "commits": commits,
        "page": page,
        "per_page": per_page,
    }, {"Cache-Control": "private, max-age=15"}


@bp.get("/commits/<string:sha>")
@login_required
def commit_detail(slug, sha):
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    try:
        detail = repo.commit_detail(sha)
    except GitServiceError as e:
        return {"error": str(e)}, 404
    return {"commit": detail}


@bp.get("/diff")
@login_required
def diff(slug):
    """提交级 diff：?sha=<sha> 或 ?from=<sha>&to=<sha>"""
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    sha = request.args.get("sha")
    from_sha = request.args.get("from")
    to_sha = request.args.get("to")
    try:
        if sha:
            commit = repo.repo.commit(sha)
            result = repo.diff_commit(commit)
        elif from_sha and to_sha:
            result = repo.diff_commits(from_sha, to_sha)
        else:
            return {"error": "缺少 sha 或 from/to 参数"}, 400
    except (GitServiceError, Exception) as e:
        return {"error": str(e)}, 404
    return result


@bp.get("/branches")
@login_required
def branches(slug):
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    return {"branches": repo.list_branches(), "default_branch": repo.default_branch()}


@bp.post("/branches")
@login_required
def create_branch(slug):
    project = project_from_slug(slug)
    if member_role(g.user, project) not in ("owner", "developer"):
        return {"error": "仅项目开发者可以创建分支"}, 403
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    source = data.get("source")
    try:
        repo.create_branch(name, source_branch=source)
    except GitServiceError as e:
        return {"error": str(e)}, 400
    return {"ok": True, "name": name}, 201


@bp.delete("/branches/<string:name>")
@login_required
def delete_branch(slug, name):
    project = project_from_slug(slug)
    if member_role(g.user, project) not in ("owner", "developer"):
        return {"error": "仅项目开发者可以删除分支"}, 403
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    try:
        repo.delete_branch(name)
    except GitServiceError as e:
        return {"error": str(e)}, 400
    return {"ok": True}


@bp.get("/tags")
@login_required
def tags(slug):
    repo, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    return {"tags": repo.list_tags()}
