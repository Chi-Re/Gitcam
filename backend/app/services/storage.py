"""MinIO 对象存储封装：预签名 URL 上传/下载（大文件与二进制文件承载）"""

import io
from datetime import timedelta

from flask import current_app
from minio import Minio
from minio.error import S3Error


def get_client():
    return Minio(
        current_app.config["MINIO_ENDPOINT"],
        access_key=current_app.config["MINIO_ACCESS_KEY"],
        secret_key=current_app.config["MINIO_SECRET_KEY"],
        secure=current_app.config["MINIO_SECURE"],
    )


def ensure_bucket():
    client = get_client()
    bucket = current_app.config["MINIO_BUCKET"]
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    return bucket


def put_object(object_name, data: bytes, content_type="application/octet-stream"):
    client = get_client()
    bucket = ensure_bucket()
    client.put_object(bucket, object_name, io.BytesIO(data), length=len(data), content_type=content_type)
    return object_name


def get_object(object_name):
    client = get_client()
    bucket = current_app.config["MINIO_BUCKET"]
    resp = client.get_object(bucket, object_name)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def presigned_upload_url(object_name, expires_minutes=30, content_type=None):
    """大文件直传：返回预签名 PUT URL 与预签名 GET URL"""
    client = get_client()
    bucket = ensure_bucket()
    upload_url = client.presigned_put_object(
        bucket, object_name, expires=timedelta(minutes=expires_minutes)
    )
    download_url = client.presigned_get_object(
        bucket, object_name, expires=timedelta(minutes=expires_minutes * 10)
    )
    return upload_url, download_url


def presigned_download_url(object_name, expires_minutes=60):
    client = get_client()
    bucket = current_app.config["MINIO_BUCKET"]
    try:
        return client.presigned_get_object(
            bucket, object_name, expires=timedelta(minutes=expires_minutes)
        )
    except S3Error:
        return None


def public_url(object_name):
    base = current_app.config["MINIO_PUBLIC_BASE_URL"].rstrip("/")
    return f"{base}/{current_app.config['MINIO_BUCKET']}/{object_name}"


def remove_object(object_name):
    client = get_client()
    bucket = current_app.config["MINIO_BUCKET"]
    try:
        client.remove_object(bucket, object_name)
        return True
    except S3Error:
        return False
