from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ddp_backend.core.database import SessionLocal
from ddp_backend.core.s3 import upload_file_to_s3, download_file_from_s3
from ddp_backend.models.models import Video, Source, Result
from ddp_backend.schemas.enums import VideoStatus, OriginPath
from ddp_backend.schemas.enums import Result as ResultEnum


def _set_video_status(db: Session, video: Video, status: VideoStatus) -> None:
    video.status = status
    db.commit()


def _upsert_source(db: Session, video_id: int, s3_key: str) -> Source:
    """
    sources.video_id 는 UNIQUE라서, 있으면 업데이트 / 없으면 생성
    """
    src = db.query(Source).filter(Source.video_id == video_id).first()
    if src:
        src.s3_path = s3_key
    else:
        src = Source(video_id=video_id, s3_path=s3_key)
        db.add(src)
    db.commit()
    return src


def _upsert_result(
    db: Session,
    *,
    user_id: int,
    video_id: int,
    is_fast: bool,
    total_result: ResultEnum,
) -> Result:
    """
    results.video_id 는 UNIQUE라서, 있으면 업데이트 / 없으면 생성
    """
    row = db.query(Result).filter(Result.video_id == video_id).first()
    if row:
        row.is_fast = is_fast
        row.total_result = total_result
    else:
        row = Result(user_id=user_id, video_id=video_id, is_fast=is_fast, total_result=total_result)
        db.add(row)
    db.commit()
    return row


def _run_dummy_inference(video_path: Path) -> ResultEnum:
    """
    모델 연결 전이라면 여기 더미로 통과.
    나중에 detect_pipeline.run(...) 같은 팀 함수로 교체하면 됨.
    """
    # TODO: 실제 추론 연결
    return ResultEnum.REAL


def process_uploaded_video(video_id: int) -> None:
    """
    업로드된 영상 처리:
    - S3에서 다운로드
    - 추론
    - results 저장
    """
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            return

        _set_video_status(db, video, VideoStatus.PROCESSING)

        source = db.query(Source).filter(Source.video_id == video_id).first()
        if not source:
            _set_video_status(db, video, VideoStatus.FAILED)
            return

        with tempfile.TemporaryDirectory() as td:
            local_path = Path(td) / f"{video_id}.mp4"
            download_file_from_s3(source.s3_path, local_path)

            total_result = _run_dummy_inference(local_path)

            _upsert_result(
                db,
                user_id=video.user_id,
                video_id=video.video_id,
                is_fast=True,
                total_result=total_result,
            )

        _set_video_status(db, video, VideoStatus.COMPLETED)

    except Exception:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if video:
            _set_video_status(db, video, VideoStatus.FAILED)
        raise
    finally:
        db.close()


def process_youtube_video(video_id: int) -> None:
    """
    유튜브 링크 처리:
    - (TODO) yt-dlp로 다운로드
    - S3 업로드
    - Source upsert
    - 추론
    - results 저장
    """
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            return

        _set_video_status(db, video, VideoStatus.PROCESSING)

        if not video.source_url:
            _set_video_status(db, video, VideoStatus.FAILED)
            return

        with tempfile.TemporaryDirectory() as td:
            local_path = Path(td) / f"{video_id}.mp4"

            # TODO: 팀에서 쓰는 유튜브 다운로드 유틸로 교체
            # 예) from ddp_backend.utils.file_handler import download_youtube
            # download_youtube(video.source_url, local_path)
            raise NotImplementedError("TODO: Implement youtube download (yt-dlp) and save to local_path")

            # S3 업로드
            # with open(local_path, "rb") as f:
            #     s3_key = upload_file_to_s3(f, f"raw/{video_id}.mp4", content_type="video/mp4")
            # _upsert_source(db, video_id=video_id, s3_key=s3_key)

            # 추론
            # total_result = _run_dummy_inference(local_path)
            # _upsert_result(db, user_id=video.user_id, video_id=video.video_id, is_fast=True, total_result=total_result)

        _set_video_status(db, video, VideoStatus.COMPLETED)

    except Exception:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if video:
            _set_video_status(db, video, VideoStatus.FAILED)
        raise
    finally:
        db.close()