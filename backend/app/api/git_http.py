"""Git Smart HTTP 协议：代理 git-http-backend，支持真实 git clone/fetch/push。

路由：/git/<slug>.git/<service>
认证：HTTP Basic（用户名=username/email/学号，密码=账号密码）
权限：读=公开项目或成员；写=Owner/Developer
"""

import base64
import os
import subprocess
import threading

from flask import Blueprint, request, Response, current_app, g

from app.models import User, Project, ProjectMember
from app.utils.decorators import member_role

bp = Blueprint("git_http", __name__, url_prefix="/git")

GIT_HTTP_BACKEND = "/usr/lib/git-core/git-http-backend"
if not os.path.exists(GIT_HTTP_BACKEND):
    GIT_HTTP_BACKEND = os.path.join(
        os.path.dirname(subprocess.run(["git", "--exec-path"], capture_output=True, text=True).stdout.strip()),
        "git-http-backend",
    )

READ_SERVICES = {"git-upload-pack", "git-receive-pack", "HEAD", "info/refs"}
WRITE_SERVICES = {"git-receive-pack"}

# 按项目粒度的 push 后处理锁（防止并发 push 时 reflog/refs 竞争）
_push_locks = {}
_push_locks_guard = threading.Lock()


def _get_push_lock(project_id):
    with _push_locks_guard:
        if project_id not in _push_locks:
            _push_locks[project_id] = threading.Lock()
        return _push_locks[project_id]


def _parse_basic_auth():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return None, None
    try:
        decoded = base64.b64decode(header[6:]).decode("utf-8", errors="replace")
    except Exception:
        return None, None
    if ":" in decoded:
        user, _, password = decoded.partition(":")
        return user, password
    return decoded, None


def _authenticate():
    """返回 (user|None, error_response|None)"""
    username, password = _parse_basic_auth()
    if not username:
        return None, None
    user = None
    if "@" in username:
        user = User.query.filter_by(email=username.lower()).first()
    if user is None:
        user = User.query.filter_by(username=username).first()
    if user is None and username.isdigit():
        user = User.query.filter_by(student_id=username).first()
    if user is None or not user.check_password(password or ""):
        return None, _auth_required()
    if not user.is_active:
        return None, _auth_required()
    return user, None


def _auth_required():
    resp = Response("Authentication required", status=401, mimetype="text/plain")
    resp.headers["WWW-Authenticate"] = 'Basic realm="gitcam"'
    return resp


def _list_branch_shas(repo_dir):
    """列出 refs/heads/* 全部分支当前 SHA（用于 push 前后对比）"""
    try:
        out = subprocess.run(
            ["git", "--git-dir", repo_dir, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        result = {}
        for line in out.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) == 2:
                result[parts[0]] = parts[1]
        return result
    except Exception:
        return {}


def _check_permission(slug, is_write, user):
    """返回 (allowed, error_response)"""
    project = Project.query.filter_by(slug=slug).first()
    if project is None:
        return False, Response("Repository not found", status=404, mimetype="text/plain")
    role = member_role(user, project)
    if is_write:
        if role in ("owner", "developer"):
            return True, None
        if user is None:
            return False, _auth_required()
        return False, Response("Permission denied: write access requires Developer role", status=403, mimetype="text/plain")
    # 读权限
    if project.visibility == "public":
        return True, None
    if role is not None:
        return True, None
    if user is None:
        return False, _auth_required()
    return False, Response("Permission denied: private repository", status=403, mimetype="text/plain")


@bp.route("/<string:slug>.git/<path:service>", methods=["GET", "POST"])
def git_service(slug, service):
    if service not in READ_SERVICES and not service.endswith("git-upload-pack") and not service.endswith("git-receive-pack"):
        return Response("Not found", status=404, mimetype="text/plain")

    is_write = service.endswith("git-receive-pack") or (service == "info/refs" and request.method == "POST")

    user, error_resp = _authenticate()
    if error_resp:
        return error_resp
    allowed, error_resp = _check_permission(slug, is_write, user)
    if not allowed:
        return error_resp

    project = Project.query.filter_by(slug=slug).first()
    repo_root = current_app.config["REPO_ROOT"]
    repo_dir = os.path.join(repo_root, f"{project.id}.git")
    if not os.path.isdir(repo_dir):
        return Response("Repository not initialized", status=404, mimetype="text/plain")

    # push 前分支 refs 快照（用于 push 后扫描新提交）
    before_refs = _list_branch_shas(repo_dir) if is_write else {}

    env = os.environ.copy()
    env.update(
        {
            "GIT_PROJECT_ROOT": repo_root,
            "GIT_HTTP_EXPORT_ALL": "1",
            "PATH_INFO": f"/{project.id}.git/{service}",
            "REQUEST_METHOD": request.method,
            "QUERY_STRING": request.query_string.decode("utf-8"),
            "CONTENT_TYPE": request.content_type or "",
            "REMOTE_ADDR": request.remote_addr or "",
        }
    )
    if user:
        env["REMOTE_USER"] = user.username
    env["HTTP_CONTENT_ENCODING"] = request.headers.get("Content-Encoding", "")

    process = subprocess.Popen(
        [GIT_HTTP_BACKEND],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        bufsize=0,
    )

    request_stream = request.stream
    stderr = b""

    def pump_input():
        try:
            while True:
                chunk = request_stream.read(65536)
                if not chunk:
                    break
                process.stdin.write(chunk)
        except (BrokenPipeError, OSError):
            pass
        finally:
            try:
                process.stdin.close()
            except Exception:
                pass

    def pump_output(stream, result):
        try:
            result.append(stream.read())
        except Exception:
            pass

    import threading

    out_chunks, err_chunks = [], []
    out_thread = threading.Thread(target=pump_output, args=(process.stdout, out_chunks), daemon=True)
    err_thread = threading.Thread(target=pump_output, args=(process.stderr, err_chunks), daemon=True)
    input_thread = threading.Thread(target=pump_input, daemon=True)
    out_thread.start()
    err_thread.start()
    input_thread.start()
    input_thread.join(timeout=60)
    process.wait(timeout=120)
    out_thread.join(timeout=10)
    err_thread.join(timeout=10)
    stdout = b"".join(out_chunks)
    stderr = b"".join(err_chunks)

    if process.returncode != 0:
        current_app.logger.warning("git-http-backend 失败(%s): %s", slug, stderr.decode(errors="replace")[:500])

    # 解析 CGI 头与正文
    head, sep, body = stdout.partition(b"\r\n\r\n")
    if not sep:
        head, sep, body = stdout.partition(b"\n\n")
    status_code = 200
    headers = {}
    if head:
        for line in head.split(b"\n"):
            line = line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line.lower().startswith("status:"):
                status_code = int(line.split(":", 1)[1].strip().split()[0])
            elif ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip()] = value.strip()

    response = Response(body, status=status_code)
    for key, value in headers.items():
        if key.lower() not in ("content-length", "transfer-encoding"):
            response.headers[key] = value
    response.headers["Content-Length"] = str(len(body))

    # 记录 push 动态 + 扫描 "fix #N" 自动关联 Issue
    if is_write and process.returncode == 0 and user:
        lock = _get_push_lock(project.id)
        with lock:
            _handle_push_events(project, repo_dir, repo_root, slug, user, before_refs)
    return response


def _handle_push_events(project, repo_dir, repo_root, slug, user, before_refs):
    """push 成功后的统一处理：动态流 / fix #N 自动关联 / 成员通知"""
    from flask import current_app
    from app.services import activity, issue as issue_service
    from app.services.notification import create_notification, notify_project_members

    try:
        from app.services.git_service import GitService
        from app.models import Issue

        repo = GitService.open(project.id)
        head_sha = None
        branch = repo.default_branch()
        try:
            head_sha = repo.repo.head.commit.hexsha
        except Exception:
            pass
        activity.record_event(
            project.id,
            user.id,
            "commit",
            "pushed",
            title=f"推送代码到 {branch}",
            ref_type="branch",
            ref_name=branch,
            commit_sha=head_sha,
            data={"via": "git http"},
        )

        # 扫描新提交：before_refs vs 当前 refs
        after_refs = _list_branch_shas(repo_dir)
        for ref, new_sha in after_refs.items():
            old_sha = before_refs.get(ref)
            if not old_sha or old_sha == new_sha:
                continue
            try:
                log = repo.repo.git.log(
                    "--format=%H%x00%s%x00%b", f"{old_sha}..{new_sha}"
                )
            except Exception:
                continue
            for block in log.split("\n\n"):
                lines = [l for l in block.splitlines() if l]
                if not lines:
                    continue
                parts = lines[0].split("\x00")
                sha = parts[0].strip()
                if not sha:
                    continue
                message = " ".join(p for p in parts[1:] if p)
                for issue_id in issue_service.parse_issue_references(message):
                    issue = Issue.query.filter_by(id=issue_id, project_id=project.id).first()
                    if issue is None:
                        continue
                    try:
                        issue_service.link_commit(issue.id, sha, user.id)
                        if issue.status in ("open", "in_progress"):
                            issue.status = "resolved"
                            activity.record_event(
                                project.id,
                                user.id,
                                "issue",
                                "status",
                                title=f"提交 {sha[:8]} 自动解决 Issue #{issue.id}：{issue.title}",
                                ref_type="branch",
                                ref_name=branch,
                                commit_sha=sha,
                                data={"issue_id": issue.id, "old": "open", "new": "resolved", "auto": True},
                            )
                            recipients = {issue.created_by, issue.assignee_id} - {user.id}
                            for uid in recipients:
                                if uid is None:
                                    continue
                                create_notification(
                                    user_id=uid,
                                    type_="issue",
                                    title=f"提交 {sha[:8]} 引用了「fix #{issue.id}」，Issue 已自动标记为已解决",
                                    project_id=project.id,
                                    url=f"/projects/{project.slug}/issues/{issue.id}",
                                )
                        else:
                            activity.record_event(
                                project.id,
                                user.id,
                                "issue",
                                "committed",
                                title=f"提交 {sha[:8]} 关联 Issue #{issue.id}：{issue.title}",
                                ref_type="branch",
                                ref_name=branch,
                                commit_sha=sha,
                                data={"issue_id": issue.id},
                            )
                    except Exception as e:
                        current_app.logger.warning("Issue 自动关联失败: %s", e)
        # 通知项目成员：仓库新动态（按 repo 偏好，跳过操作者）
        try:
            if after_refs != before_refs:
                notify_project_members(
                    project.id,
                    "repo",
                    title=f"{user.full_name} 推送了代码到 {branch}",
                    content=(head_sha or "")[:8],
                    url=f"/projects/{project.slug}/commits/{head_sha}" if head_sha else None,
                    exclude_user_id=user.id,
                )
        except Exception as e:
            current_app.logger.warning("push 成员通知失败: %s", e)
        activity.db.session.commit()
    except Exception as e:
        current_app.logger.warning("记录 push 动态失败: %s", e)
