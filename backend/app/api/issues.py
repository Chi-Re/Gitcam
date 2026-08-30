"""Issue API：CRUD/评论/状态流转/关联提交"""

from flask import Blueprint, request, g

from app.extensions import db
from app.models import Issue, IssueComment, ISSUE_STATUSES, ISSUE_PRIORITIES
from app.services import issue as issue_service, activity
from app.services.notification import create_notification
from app.utils.decorators import (
    login_required,
    project_from_slug,
    member_role,
    project_visible,
    is_owner_or_admin,
)

bp = Blueprint("issues", __name__, url_prefix="/api/projects/<string:slug>/issues")


def _check_access(slug, min_role="viewer"):
    project = project_from_slug(slug)
    role = member_role(g.user, project)
    if role is None:
        if project.visibility == "public" and min_role == "viewer":
            return project, "viewer", None, None
        return None, None, "无权访问该项目", 403
    return project, role, None, None


def _notify_assignee(project, issue, assignee):
    if not assignee or assignee.id == g.user.id:
        return
    create_notification(
        user_id=assignee.id,
        type_="issue",
        title=f"你被指派到 Issue #{issue.id}：{issue.title}",
        content=(issue.description or "")[:200] or None,
        project_id=project.id,
        url=f"/projects/{project.slug}/issues/{issue.id}",
    )


def _notify_status_change(project, issue, new_status):
    """通知创建者与指派人（发起者本人除外）"""
    recipients = {issue.created_by, issue.assignee_id} - {g.user.id}
    for uid in recipients:
        if uid is None:
            continue
        create_notification(
            user_id=uid,
            type_="issue",
            title=f"Issue #{issue.id} 状态变更为「{issue_service.STATUS_LABELS.get(new_status, new_status)}」：{issue.title}",
            project_id=project.id,
            url=f"/projects/{project.slug}/issues/{issue.id}",
        )


@bp.get("")
@login_required
def list_issues(slug):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    status = request.args.get("status", "all")
    priority = request.args.get("priority", "all")
    label = request.args.get("label", "")
    assignee = request.args.get("assignee", "")
    milestone = request.args.get("milestone", "")
    sort = request.args.get("sort", "latest")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)

    query = Issue.query.filter_by(project_id=project.id)
    if status and status != "all":
        query = query.filter_by(status=status)
    if priority and priority != "all":
        query = query.filter_by(priority=priority)
    if label:
        query = query.filter(Issue.labels.like(f"%{label}%"))
    if assignee == "none":
        query = query.filter(Issue.assignee_id.is_(None))
    elif assignee:
        query = query.filter(Issue.assignee_id == int(assignee))
    if milestone:
        query = query.filter_by(milestone=milestone)

    total = query.count()
    if sort == "priority":
        order = {
            "urgent": 0, "high": 1, "medium": 2, "low": 3,
        }
        issues = query.all()
        issues.sort(key=lambda i: (order.get(i.priority, 9), -i.id))
        items = issues[(page - 1) * per_page: page * per_page]
    else:
        items = (
            query.order_by(Issue.updated_at.desc(), Issue.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
    return {"total": total, "items": [i.to_dict() for i in items], "page": page, "per_page": per_page}


@bp.post("")
@login_required
def create_issue(slug):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return {"error": "请填写标题"}, 400
    priority = data.get("priority") or "medium"
    if priority not in ISSUE_PRIORITIES:
        return {"error": "优先级不合法"}, 400

    issue = Issue(
        project_id=project.id,
        title=title,
        description=(data.get("description") or "").strip() or None,
        priority=priority,
        labels=",".join([l.strip() for l in (data.get("labels") or []) if l.strip()]) or None,
        milestone=(data.get("milestone") or "").strip() or None,
        assignee_id=data.get("assignee_id"),
        created_by=g.user.id,
    )
    db.session.add(issue)
    db.session.flush()

    _notify_assignee(project, issue, issue.assignee)
    activity.record_event(
        project.id, g.user.id, "issue", "created",
        title=f"创建 Issue #{issue.id}：{title}",
        data={"issue_id": issue.id},
    )
    db.session.commit()
    return {"issue": issue.to_dict(detail=True)}, 201


@bp.get("/<int:issue_id>")
@login_required
def get_issue(slug, issue_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    issue = Issue.query.filter_by(id=issue_id, project_id=project.id).first()
    if issue is None:
        return {"error": "Issue 不存在"}, 404
    return {"issue": issue.to_dict(detail=True)}


@bp.put("/<int:issue_id>")
@login_required
def update_issue(slug, issue_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    issue = Issue.query.filter_by(id=issue_id, project_id=project.id).first()
    if issue is None:
        return {"error": "Issue 不存在"}, 404
    if not issue_service.can_manage_issue(g.user, project, issue):
        return {"error": "仅创建者/指派人/项目Owner可以编辑"}, 403
    data = request.get_json(silent=True) or {}
    old_assignee = issue.assignee_id
    if "title" in data and data["title"]:
        issue.title = (data["title"] or "").strip()
    if "description" in data:
        issue.description = (data["description"] or "").strip() or None
    if "priority" in data and data["priority"] in ISSUE_PRIORITIES:
        issue.priority = data["priority"]
    if "labels" in data:
        issue.labels = ",".join([l.strip() for l in data["labels"] if l.strip()]) or None
    if "milestone" in data:
        issue.milestone = (data["milestone"] or "").strip() or None
    if "assignee_id" in data:
        issue.assignee_id = data["assignee_id"] or None
    if "status" in data:
        try:
            issue_service.change_status(g.user, project, issue, data["status"])
        except (PermissionError, ValueError) as e:
            return {"error": str(e)}, 400
    if old_assignee != issue.assignee_id:
        _notify_assignee(project, issue, issue.assignee)
    activity.record_event(
        project.id, g.user.id, "issue", "updated",
        title=f"更新 Issue #{issue.id}：{issue.title}",
        data={"issue_id": issue.id},
    )
    db.session.commit()
    return {"issue": issue.to_dict(detail=True)}


@bp.delete("/<int:issue_id>")
@login_required
def delete_issue(slug, issue_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    issue = Issue.query.filter_by(id=issue_id, project_id=project.id).first()
    if issue is None:
        return {"error": "Issue 不存在"}, 404
    if issue.created_by != g.user.id and not is_owner_or_admin(project, g.user):
        return {"error": "仅创建者或项目Owner可以删除"}, 403
    from app.services import audit

    audit.record("delete_issue", "issue", issue.id, {"title": issue.title, "project_id": project.id})
    db.session.delete(issue)
    activity.record_event(
        project.id, g.user.id, "issue", "deleted",
        title=f"删除 Issue #{issue.id}：{issue.title}",
    )
    db.session.commit()
    return {"ok": True}


@bp.post("/<int:issue_id>/status")
@login_required
def change_status(slug, issue_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    issue = Issue.query.filter_by(id=issue_id, project_id=project.id).first()
    if issue is None:
        return {"error": "Issue 不存在"}, 404
    data = request.get_json(silent=True) or {}
    target = data.get("status", "")
    try:
        old = issue_service.change_status(g.user, project, issue, target)
    except (PermissionError, ValueError) as e:
        return {"error": str(e)}, 400
    if old:
        activity.record_event(
            project.id, g.user.id, "issue", "status",
            title=f"Issue #{issue.id} 状态：{issue_service.STATUS_LABELS.get(old, old)} → {issue_service.STATUS_LABELS.get(target, target)}",
            data={"issue_id": issue.id, "old": old, "new": target},
        )
        _notify_status_change(project, issue, target)
    db.session.commit()
    return {"issue": issue.to_dict(detail=True)}


# ---------- 评论 ----------

@bp.post("/<int:issue_id>/comments")
@login_required
def create_comment(slug, issue_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    issue = Issue.query.filter_by(id=issue_id, project_id=project.id).first()
    if issue is None:
        return {"error": "Issue 不存在"}, 404
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return {"error": "评论内容不能为空"}, 400
    comment = IssueComment(issue_id=issue.id, author_id=g.user.id, content=content)
    db.session.add(comment)
    issue.comment_count += 1

    recipients = {issue.created_by, issue.assignee_id, *[c.author_id for c in issue.comments]} - {g.user.id}
    for uid in recipients:
        if uid is None:
            continue
        create_notification(
            user_id=uid,
            type_="issue",
            title=f"{g.user.full_name} 评论了 Issue #{issue.id}：{issue.title}",
            content=(content or "")[:200],
            project_id=project.id,
            url=f"/projects/{project.slug}/issues/{issue.id}",
        )
    activity.record_event(
        project.id, g.user.id, "issue", "commented",
        title=f"评论 Issue #{issue.id}：{issue.title}",
        data={"issue_id": issue.id},
    )
    db.session.commit()
    return {"comment": comment.to_dict()}, 201


@bp.delete("/<int:issue_id>/comments/<int:comment_id>")
@login_required
def delete_comment(slug, issue_id, comment_id):
    project, role, error, code = _check_access(slug)
    if error:
        return {"error": error}, code
    comment = IssueComment.query.filter_by(id=comment_id, issue_id=issue_id).first()
    if comment is None:
        return {"error": "评论不存在"}, 404
    if comment.author_id != g.user.id and not is_owner_or_admin(project, g.user):
        return {"error": "仅作者或管理员可以删除评论"}, 403
    issue = Issue.query.get(issue_id)
    if issue:
        issue.comment_count = max(0, issue.comment_count - 1)
    db.session.delete(comment)
    db.session.commit()
    return {"ok": True}
