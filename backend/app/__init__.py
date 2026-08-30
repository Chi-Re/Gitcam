from flask import Flask, jsonify, request
from sqlalchemy import text

from app.config import Config
from app.extensions import db, jwt, migrate, cors

COMPOSITE_INDEXES = [
    "CREATE INDEX ix_activity_project_time ON activity_events (project_id, created_at DESC)",
    "CREATE INDEX ix_posts_project_time ON posts (project_id, created_at DESC)",
    "CREATE INDEX ix_issues_project_status ON issues (project_id, status)",
    "CREATE INDEX ix_notifications_user_read ON notifications (user_id, is_read)",
    "CREATE INDEX ix_wiki_project ON wiki_pages (project_id)",
]


def _ensure_indexes(app):
    """幂等创建复合索引（MySQL 8 不支持 CREATE INDEX IF NOT EXISTS，先查 information_schema）"""
    with app.app_context():
        db_name = app.config["SQLALCHEMY_DATABASE_URI"].split("/")[-1].split("?")[0]
        existing = set()
        rows = db.session.execute(
            text(
                "SELECT TABLE_NAME, INDEX_NAME FROM information_schema.statistics "
                "WHERE TABLE_SCHEMA = :db"
            ),
            {"db": db_name},
        ).fetchall()
        for table, index in rows:
            existing.add(f"{table}.{index}")
        for sql in COMPOSITE_INDEXES:
            name = sql.split("ix_")[1].split(" ")[0]
            table = sql.split(" ON ")[1].split(" ")[0]
            if f"{table}.ix_{name}" in existing:
                continue
            db.session.execute(text(sql))
        db.session.commit()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    from app.api import register_blueprints

    register_blueprints(app)

    @app.before_request
    def before_request():
        import time as _time
        request._gitcam_start = _time.perf_counter()

    @app.after_request
    def after_request(resp):
        import time as _time
        start = getattr(request, "_gitcam_start", None)
        if start is not None:
            duration_ms = round((_time.perf_counter() - start) * 1000, 1)
            resp.headers["X-Process-Time-MS"] = str(duration_ms)
        return resp

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": getattr(e, "description", "请求参数错误")}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": getattr(e, "description", "未授权")}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": getattr(e, "description", "禁止访问")}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": getattr(e, "description", "资源不存在")}), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("服务器内部错误")
        return jsonify({"error": "服务器内部错误"}), 500

    @app.errorhandler(Exception)
    def unhandled(e):
        from sqlalchemy.exc import SQLAlchemyError

        if isinstance(e, SQLAlchemyError):
            db.session.rollback()
        app.logger.exception("未处理异常")
        return jsonify({"error": "服务器内部错误"}), 500

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.cli.command("ensure-indexes")
    def ensure_indexes_cmd():
        """幂等创建复合索引（启动时执行）"""
        _ensure_indexes(app)
        print("复合索引就绪")

    return app
