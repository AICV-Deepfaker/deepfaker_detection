from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException, status

from ddp_backend.core.config import settings


def _get_s3_client():
    kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


# =========
# User
# =========

# 프로필 이미지 업로드
# key: profiles/{user_id} (확장자 없이 덮어쓰기 방식)
def upload_image_to_s3(file: UploadFile, user_id: str) -> str:
    if not settings.AWS_S3_BUCKET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 버킷이 설정되지 않았습니다"
        )
    s3 = _get_s3_client()
    key = f"profiles/{user_id}"
    try:
        s3.upload_fileobj(
            file.file,
            settings.AWS_S3_BUCKET,
            key,
            ExtraArgs={"ContentType": file.content_type or "image/jpeg"},
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이미지 업로드 실패: {e}"
        )
    return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


# 프로필 이미지 삭제
def delete_image_from_s3(url: str):
    if not settings.AWS_S3_BUCKET:
        return
    # URL에서 key 추출: https://bucket.s3.region.amazonaws.com/profiles/xxx
    if ".amazonaws.com/" not in url:
        return
    key = url.split(".amazonaws.com/", 1)[-1]
    s3 = _get_s3_client()
    try:
        s3.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
    except ClientError:
        pass  # 삭제 실패해도 진행


# 회원탈퇴 시 s3_path를 확인하여 즉각 삭제
def delete_video_from_s3(url: str):
    if not settings.AWS_S3_BUCKET or ".amazonaws.com/" not in url:
        return
    key = url.split(".amazonaws.com/", 1)[-1]
    s3 = _get_s3_client()
    try:
        s3.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
    except ClientError:
        pass


def upload_video_to_s3(file, filename: str | Path) -> str:
    return ""


def download_video_from_s3(url: str, download_path: Path) -> Path:
    return download_path
