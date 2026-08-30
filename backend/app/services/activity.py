"""项目动态聚合：各模块统一通过本服务写入 ActivityEvent"""

from app.extensions import db
from app.models.activity import ActivityEvent


def record_event(project_id, actor_id, event_type, action="created", title=None,
                 ref_type=None, ref_name=None, commit_sha=None, data=None):
    event = ActivityEvent(
        project_id=project_id,
        actor_id=actor_id,
        event_type=event_type,
        action=action,
        title=title,
        ref_type=ref_type,
        ref_name=ref_name,
        commit_sha=commit_sha,
        data=data,
    )
    db.session.add(event)
    return event


def query_events(project_id, event_type=None, page=1, per_page=30):
    q = ActivityEvent.query.filter_by(project_id=project_id)
    if event_type and event_type != "all":
        q = q.filter_by(event_type=event_type)
    total = q.count()
    events = (
        q.order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {"total": total, "items": [e.to_dict() for e in events]}
