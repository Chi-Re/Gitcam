"""对象存储 API：预签名上传/下载（大文件与二进制承载）"""

import uuid
from datetime import datetime

from flask import Blueprint, request, g, current_app

from app.services import storage
from app.utils.decorators import login_required

bp = Blueprint("storage_api", __name__, url_prefix="/api/storage")


@bp.post("/upload-url")
@login_required
def presigned_upload():
    """获取预签名直传 URL：{filename, content_type} -> {upload_url, download_url, object_name}"""
    data = request.get_json(silent=True) or {}
    filename = (data.get("filename") or "").strip()
    if not filename:
        return {"error": "缺少文件名"}, 400
    content_type = data.get("content_type") or "application/octet-stream"
    object_name = f"uploads/{datetime.now().strftime('%Y%m')}/{uuid.uuid4().hex}/{filename}"
    try:
        upload_url, download_url = storage.presigned_upload_url(object_name, content_type=content_type)
    except Exception as e:
        current_app.logger.warning("获取上传 URL 失败: %s", e)
        return {"error": "存储服务不可用"}, 503
    return {"upload_url": upload_url, "download_url": download_url, "object_name": object_name}


@bp.get("/download-url")
@login_required
def presigned_download():
    object_name = request.args.get("object_name", "")
    if not object_name:
        return {"error": "缺少 object_name"}, 400
    url = storage.presigned_download_url(object_name)
    if not url:
        return {"error": "文件不存在"}, 404
    return {"download_url": url}
