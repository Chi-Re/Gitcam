"""Issue 服务：状态流转/权限/提交关键字解析"""

import re

from app.extensions import db
from app.models import Issue, IssueCommit, ISSUE_STATUSES, STATUS_LABELS

# 提交信息中的 Issue 关键字："fix #12" "closes #34" 等
ISSUE_KEYWORD_RE = re.compile(
    r"\b(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved|解决|修复)\s+#(\d+)\b",
    re.IGNORECASE,
)

STATUS_TRANSITIONS = {
    "open": ("in_progress", "resolved", "closed"),
    "in_progress": ("open", "resolved", "closed"),
    "resolved": ("open", "closed"),
    "closed": ("open",),
}


def can_manage_issue(user, project, issue):
    """状态/编辑权限：创建者/指派人/项目Owner/教师/管理员"""
    if user is None:
        return False
    if user.role in ("teacher", "admin"):
        return True
    if issue.created_by == user.id:
        return True
    if issue.assignee_id == user.id:
        return True
    return project.owner_id == user.id


def can_transition(current, target):
    return target in STATUS_TRANSITIONS.get(current, ())


def change_status(user, project, issue, target):
    if target not in ISSUE_STATUSES:
        raise ValueError("状态不合法")
    if not can_manage_issue(user, project, issue):
        raise PermissionError("仅创建者/指派人/项目Owner可以修改状态")
    if target == issue.status:
        return False
    if target == "closed":
        from datetime import datetime, timezone
        issue.closed_at = datetime.now(timezone.utc)
    elif issue.status == "closed" and target != "closed":
        issue.closed_at = None
    old = issue.status
    issue.status = target
    return old


def parse_issue_references(message):
    """从提交信息提取引用的 Issue 编号列表（去重保序）"""
    return list(dict.fromkeys(int(m) for m in ISSUE_KEYWORD_RE.findall(message or "")))


def find_commits_by_regex(repo, start_sha, end_sha):
    """返回 (sha, message) 列表"""
    try:
        log = repo.repo.git.log("--format=%H%x00%s%x00%b", f"{start_sha}..{end_sha}")
    except Exception:
        return []
    result = []
    for block in log.strip().split("\n\n"):
        if not block:
            continue
        lines = block.splitlines()
        if not lines:
            continue
        sha = lines[0].split("\x00")[0].strip()
        if not sha:
            continue
        msg_lines = [l.split("\x00", 1)[-1] for l in lines if "\x00" in l]
        message = " ".join(msg_lines) if msg_lines else sha
        result.append((sha, message))
    return result


def link_commit(issue_id, commit_sha, linked_by):
    existing = IssueCommit.query.filter_by(issue_id=issue_id, commit_sha=commit_sha).first()
    if existing:
        return existing
    link = IssueCommit(issue_id=issue_id, commit_sha=commit_sha, linked_by=linked_by)
    db.session.add(link)
    db.session.flush()
    return link
