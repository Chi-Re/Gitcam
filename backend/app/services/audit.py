"""审计日志服务：敏感操作统一记录"""

import json

from flask import g, request

from app.extensions import db
from app.models.admin import AuditLog


def record(action, target_type=None, target_id=None, detail=None):
    """记录敏感操作；actor 取自 g.user"""
    log = AuditLog(
        actor_id=g.user.id if hasattr(g, "user") and g.user else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        ip=request.remote_addr if request else None,
    )
    db.session.add(log)
    return log
