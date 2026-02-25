from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from sqlmodel.orm.session import Session

from ddp_backend.core.database import get_db
from ddp_backend.core.s3 import upload_file_to_s3, download_file_from_s3
from ddp_backend.models.models import Video, Source, Result
from ddp_backend.schemas.enums import VideoStatus
from ddp_backend.schemas.enums import Result as ResultEnum
from ddp_backend.services.crud import CRUDSource, CRUDVideo, CRUDResult
import subprocess
import shutil

def _set_video_status(db: Session, video: Video, status: VideoStatus) -> None:
    CRUDVideo.update_status(db, video.video_id, status)


def _upsert_source(db: Session, video_id: uuid.UUID, s3_key: str) -> Source:
    """
    sources.video_id 는 UNIQUE라서, 있으면 업데이트 / 없으면 생성
    """
    return CRUDSource.upsert_source(db, video_id, s3_key)

def _upsert_result(
    db: Session,
    *,
    user_id: uuid.UUID,
    video_id: uuid.UUID,
    is_fast: bool,
    total_result: ResultEnum,
) -> Result:
    """
    results.video_id 는 UNIQUE라서, 있으면 업데이트 / 없으면 생성
    """
    row = CRUDResult.get_by_video_id(db, video_id)
    if row:
        row_res = CRUDResult.update(db, row.result_id, is_fast, total_result) 
        assert row_res is not None
        return row_res
    
    row = Result(user_id=user_id, video_id=video_id, is_fast=is_fast, total_result=total_result)
    return CRUDResult.create(db, row)


def _run_dummy_inference(video_path: Path) -> ResultEnum:
    """
    모델 연결 전이라면 여기 더미로 통과.
    나중에 detect_pipeline.run(...) 같은 팀 함수로 교체하면 됨.
    """
    # TODO: 실제 추론 연결
    return ResultEnum.REAL


def process_uploaded_video(video_id: uuid.UUID) -> None:
    """
    업로드된 영상 처리:
    - S3에서 다운로드
    - 추론
    - results 저장
    """
    db = get_db()
    try:
        video = CRUDVideo.get_by_id(db, video_id)
        if not video:
            return

        _set_video_status(db, video, VideoStatus.PROCESSING)

        source = CRUDSource.get_by_video(db, video_id)
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
        video = CRUDVideo.get_by_id(db, video_id)
        if video:
            _set_video_status(db, video, VideoStatus.FAILED)
        raise
    finally:
        db.close()



# _set_video_status, _upsert_source, _upsert_result 등은 기존에 있던 유틸 그대로 사용한다고 가정


def _ensure_parent_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _download_youtube_to_path(url: str, local_path: str | Path) -> str:
    # ✅ 결과 저장 (임시: 아직 실제 추론 연결 전이므로 UNKNOWN)
    """
    Download a YouTube (or supported) URL to `local_path` using yt-dlp.
    Returns the final file path (as str).
    """
    local_path = Path(local_path)
    _ensure_parent_dir(local_path)

    # yt-dlp는 실제 저장 확장자가 달라질 수 있으니 템플릿 기반으로 받고,
    # 끝나고 가장 최근 파일을 찾아 local_path로 move해서 통일한다.
    p = local_path
    template = str(p.with_suffix("")) + ".%(ext)s"

    has_ffmpeg = shutil.which("ffmpeg") is not None

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--no-part",
        "-o", template,
    ]

    if has_ffmpeg:
        cmd += ["-f", "bv*+ba/best"]
        cmd += ["--merge-output-format", "mp4"]
    else:
        cmd += ["-f", "best"]

    cmd.append(url)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {proc.stderr.strip() or proc.stdout.strip()}")

    # 가장 최근 생성 파일을 찾아서 local_path로 맞춤
    candidates = sorted(
        p.parent.glob(p.stem + ".*"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise RuntimeError("yt-dlp finished but output file not found")

    final_path = candidates[0]

    if final_path != p:
        _ensure_parent_dir(p)
        shutil.move(str(final_path), str(p))

    return str(p)


def process_youtube_video(video_id: uuid.UUID) -> None:
    print(f"[BG] process_youtube_video start video_id={video_id}")
    """
    유튜브 링크 처리:
    - yt-dlp로 다운로드
    - (옵션) S3 업로드
    - Source upsert
    - 추론
    - results 저장
    """
    db = get_db()
    try:
        video = CRUDVideo.get_by_id(db, video_id)
        if not video:
            return

        _set_video_status(db, video, VideoStatus.PROCESSING)
        print(f"[BG] set status=PROCESSING video_id={video_id}")
        if not video.source_url:
            _set_video_status(db, video, VideoStatus.FAILED)
            return

        with tempfile.TemporaryDirectory() as td:
            local_path = Path(td) / f"{video_id}.mp4"

            # ✅ 유튜브 다운로드
            _download_youtube_to_path(str(video.source_url), local_path)
            total_result = ResultEnum.UNKNOWN

            _upsert_result(
                db,
                user_id=video.user_id,
                video_id=video.video_id,
                is_fast=True,
                total_result=total_result,
                )
            # ✅ S3 업로드 / Source upsert
            with open(local_path, "rb") as f:
                s3_key = upload_file_to_s3(
                 f,
                 f"raw/{video_id}.mp4",
                content_type="video/mp4",
                    )

            _upsert_source(db, video_id=video_id, s3_key=s3_key)

            # ✅ (옵션) 추론 / 결과 저장
            total_result = _run_dummy_inference(local_path)
            _upsert_result(db, user_id=video.user_id, video_id=video.video_id, is_fast=True, total_result=total_result)

        _set_video_status(db, video, VideoStatus.COMPLETED)

    except Exception:
        video = CRUDVideo.get_by_id(db, video_id)
        if video:
            _set_video_status(db, video, VideoStatus.FAILED)
        raise
    finally:
        db.close()