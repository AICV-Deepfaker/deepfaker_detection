from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import BinaryIO, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from fastapi import UploadFile, HTTPException, status

from ddp_backend.core.config import settings

# =========================
# ENV
# =========================
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_PUBLIC_BASE = os.getenv("S3_PUBLIC_BASE", "")  # 예: https://{bucket}.s3.{region}.amazonaws.com

# 개발 중 AWS 설정이 없을 때 서버가 죽지 않게
S3_DRY_RUN = os.getenv("S3_DRY_RUN", "0") == "1"


def _require_bucket():
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET env is not set")

def _get_s3_client():
    kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)

def _s3_client():
    return boto3.client("s3", region_name=AWS_REGION)


def _normalize_key(key: str) -> str:
    # key가 "s3://bucket/xxx" 형태로 들어오면 버킷 부분 제거
    if key.startswith("s3://"):
        # s3://bucket_name/path/to/file
        parts = key.replace("s3://", "").split("/", 1)
        return parts[1] if len(parts) == 2 else ""
    return key.lstrip("/")


def _build_public_url(key: str) -> str:
    key = _normalize_key(key)
    if S3_PUBLIC_BASE:
        return f"{S3_PUBLIC_BASE.rstrip('/')}/{key}"
    # base가 없으면 표준 s3 url 형태
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


# =========================
# Core APIs (권장 표준)
# =========================
def upload_file_to_s3(
    fileobj: BinaryIO,
    key: str,
    content_type: Optional[str] = None,
) -> str:
    """
    S3 업로드 표준 함수.
    - fileobj: UploadFile.file 같은 바이너리 스트림
    - key: "raw/xxx.mp4" 같은 S3 key
    - return: 업로드된 key
    """
    _require_bucket()
    key = _normalize_key(key)

    if S3_DRY_RUN:
        # 개발 환경에서 AWS 없이도 flow 테스트 가능
        return key

    extra = {}
    if content_type:
        extra["ContentType"] = content_type

    try:
        _s3_client().upload_fileobj(fileobj, S3_BUCKET, key, ExtraArgs=extra or None)
        return key
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"S3 upload failed: {e}") from e


def download_file_from_s3(key_or_url: str, download_path: str | Path) -> Path:
    """
    S3 다운로드 표준 함수.
    - key_or_url: "raw/xxx.mp4" 또는 "s3://bucket/raw/xxx.mp4" 또는 https url
    - download_path: 로컬 저장 경로
    - return: Path(download_path)
    """
    _require_bucket()

    # https url이면 key만 뽑아보자
    key = key_or_url
    if key_or_url.startswith("http"):
        # https://{bucket}.s3.../{key}
        # 마지막 / 이후를 key로 간주
        key = key_or_url.split("/", 3)[-1] if "/" in key_or_url else key_or_url

    key = _normalize_key(key)
    download_path = Path(download_path)

    download_path.parent.mkdir(parents=True, exist_ok=True)

    if S3_DRY_RUN:
        # dry-run이면 파일을 만들지 않고 경로만 반환
        return download_path

    try:
        _s3_client().download_file(S3_BUCKET, key, str(download_path))
        return download_path
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"S3 download failed: {e}") from e


def delete_file_from_s3(key_or_url: str) -> None:
    _require_bucket()
    key = key_or_url
    if key_or_url.startswith("http"):
        key = key_or_url.split("/", 3)[-1] if "/" in key_or_url else key_or_url
    key = _normalize_key(key)

    if S3_DRY_RUN:
        return

    try:
        _s3_client().delete_object(Bucket=S3_BUCKET, Key=key)
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"S3 delete failed: {e}") from e


# =========================
# Team legacy APIs (기존 이름 호환)
# =========================
# 프로필 이미지 업로드
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



def delete_video_from_s3(url: str):
    delete_file_from_s3(url)


def upload_video_to_s3(file, filename: str | Path) -> str:
    """
    기존 팀 함수명 유지.
    filename을 key로 쓰되, raw/ prefix 자동 부여
    """
    name = Path(filename).name
    key = f"raw/{name}"
    return upload_file_to_s3(file, key, content_type="video/mp4")


def download_video_from_s3(url: str, download_path: Path) -> Path:
    return download_file_from_s3(url, download_path)


# =========================
# Extra compatibility layer (네 코드/app 코드 호환)
# =========================
def upload_to_s3(*args, **kwargs) -> str:
    """
    어떤 코드가 upload_to_s3(file, key) 처럼 불러도 대응.
    """
    if "fileobj" in kwargs and "key" in kwargs:
        return upload_file_to_s3(kwargs["fileobj"], kwargs["key"], kwargs.get("content_type"))
    if len(args) >= 2:
        return upload_file_to_s3(args[0], args[1], kwargs.get("content_type"))
    raise TypeError("upload_to_s3 expects (fileobj, key[, content_type])")


def download_from_s3(*args, **kwargs) -> Path:
    """
    download_from_s3(key_or_url, path) 호환.
    """
    if "key_or_url" in kwargs and "download_path" in kwargs:
        return download_file_from_s3(kwargs["key_or_url"], kwargs["download_path"])
    if len(args) >= 2:
        return download_file_from_s3(args[0], args[1])
    raise TypeError("download_from_s3 expects (key_or_url, download_path)")