"""用户认证：注册 / 登录 / 当前用户 / 个人资料"""

import re

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User, UserLoginLog
from app.utils.decorators import login_required

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    role = data.get("role") or "student"
    student_id = (data.get("student_id") or "").strip() or None

    if not EMAIL_RE.match(email):
        return {"error": "邮箱格式不正确"}, 400
    if len(username) < 2 or len(username) > 32 or not re.match(r"^[\w.-]+$", username):
        return {"error": "用户名需为 2-32 位字母/数字/下划线"}, 400
    if len(password) < 6:
        return {"error": "密码至少 6 位"}, 400
    if not full_name:
        return {"error": "请填写姓名"}, 400
    if role not in ("student", "teacher"):
        return {"error": "角色只能是学生或教师（管理员由后台指派）"}, 400

    if User.query.filter_by(email=email).first():
        return {"error": "该邮箱已被注册"}, 409
    if User.query.filter_by(username=username).first():
        return {"error": "该用户名已被占用"}, 409
    if student_id and User.query.filter_by(student_id=student_id).first():
        return {"error": "该学号已被注册"}, 409

    user = User(
        email=email,
        username=username,
        full_name=full_name,
        role=role,
        student_id=student_id,
        college=(data.get("college") or "").strip() or None,
        major_class=(data.get("major_class") or "").strip() or None,
        bio=(data.get("bio") or "").strip() or None,
    )
    user.password = password
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": "注册信息冲突，请检查邮箱/用户名/学号"}, 409

    token = create_access_token(identity=str(user.id))
    return {"token": token, "user": user.to_dict()}, 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    account = (data.get("account") or "").strip()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))

    if not account or not password:
        return {"error": "请输入账号和密码"}, 400

    user = None
    if "@" in account:
        user = User.query.filter_by(email=account.lower()).first()
    if user is None:
        user = User.query.filter_by(username=account).first()
    if user is None and account.isdigit():
        user = User.query.filter_by(student_id=account).first()

    log = UserLoginLog(user_id=user.id if user else None, ip=request.remote_addr,
                       user_agent=(request.user_agent.string or "")[:255])
    db.session.add(log)

    if user is None or not user.check_password(password):
        db.session.commit()
        return {"error": "账号或密码错误"}, 401
    if not user.is_active:
        db.session.commit()
        return {"error": "账号已被禁用，请联系管理员"}, 403

    log.success = True
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        expires_delta=None if remember else None,
    )
    return {"token": token, "user": user.to_dict()}


@bp.get("/me")
@login_required
def me():
    from flask import g
    return {"user": g.user.to_dict()}


@bp.put("/profile")
@login_required
def update_profile():
    from flask import g
    data = request.get_json(silent=True) or {}
    user = g.user
    for field in ("full_name", "college", "major_class", "bio", "avatar_url", "github_url", "gitee_url"):
        if field in data:
            value = (data[field] or "").strip() or None
            if field == "bio" and value and len(value) > 500:
                return {"error": "简介过长"}, 400
            setattr(user, field, value)
    if "password" in data and data.get("password"):
        if not user.check_password(data.get("old_password") or ""):
            return {"error": "原密码错误"}, 400
        if len(data["password"]) < 6:
            return {"error": "新密码至少 6 位"}, 400
        user.password = data["password"]
    db.session.commit()
    return {"user": user.to_dict()}
