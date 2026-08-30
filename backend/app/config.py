import os
from datetime import timedelta


class Config:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    SECRET_KEY = os.environ.get("SECRET_KEY", "gitcam-dev-secret-key-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get("JWT_EXPIRE_HOURS", "24")))

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://gitcam:gitcam_dev@127.0.0.1:3306/gitcam?charset=utf8mb4",
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 3600}

    JSON_AS_ASCII = False

    # Git 仓库根目录（bare repos）
    REPO_ROOT = os.environ.get("REPO_ROOT", os.path.join(BASE_DIR, "data", "repos"))
    UPLOAD_ROOT = os.environ.get("UPLOAD_ROOT", os.path.join(BASE_DIR, "data", "uploads"))

    # MinIO 对象存储
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "127.0.0.1:9000")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "gitcam_minio")
    MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "gitcam_minio_dev")
    MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "gitcam-files")
    MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
    MINIO_PUBLIC_BASE_URL = os.environ.get("MINIO_PUBLIC_BASE_URL", "http://127.0.0.1:9000")

    # 站点外部访问地址（git clone 提示用）
    EXTERNAL_BASE_URL = os.environ.get("EXTERNAL_BASE_URL", "http://127.0.0.1:5000")

    # 邮件通知（可配置，未配置则静默降级为站内通知）
    MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "false").lower() == "true"
    MAIL_SMTP_HOST = os.environ.get("MAIL_SMTP_HOST", "")
    MAIL_SMTP_PORT = int(os.environ.get("MAIL_SMTP_PORT", "465"))
    MAIL_SMTP_USER = os.environ.get("MAIL_SMTP_USER", "")
    MAIL_SMTP_PASSWORD = os.environ.get("MAIL_SMTP_PASSWORD", "")
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "true").lower() == "true"
    MAIL_FROM = os.environ.get("MAIL_FROM", "gitcam@localhost")

    # Git HTTP 传输（smart protocol）
    GIT_HTTP_MAX_REQUEST = int(os.environ.get("GIT_HTTP_MAX_REQUEST", "10485760"))
