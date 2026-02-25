from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from ddp_backend.core.database import get_db_ctx
from ddp_backend.core.s3 import upload_file_to_s3
from ddp_backend.models.models import Source
from ddp_backend.schemas.enums import VideoStatus
from ddp_backend.services.crud import CRUDSource, CRUDVideo

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

    _COOKIES_PATH = Path(__file__).parent.parent / "cookies.txt"

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--no-part",
        "-o",
        template,
    ]

    if _COOKIES_PATH.exists():
        cmd += ["--cookies", str(_COOKIES_PATH)]

    if has_ffmpeg:
        cmd += ["-f", "bv*+ba/best"]
        cmd += ["--merge-output-format", "mp4"]
    else:
        cmd += ["-f", "best"]

    cmd.append(url)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )

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


def upload_youtube_video(video_id: uuid.UUID) -> None:
    print(f"[BG] process_youtube_video start video_id={video_id}")
    """
    유튜브 링크 처리:
    - yt-dlp로 다운로드
    - (옵션) S3 업로드
    - Source upsert
    - 추론
    - results 저장
    """
    with get_db_ctx() as db:
        video = CRUDVideo.get_by_id(db, video_id)
        if not video:
            return

        if not video.source_url:
            return

        with tempfile.TemporaryDirectory() as td:
            local_path = Path(td) / f"{video_id}.mp4"

            # ✅ 유튜브 다운로드
            _download_youtube_to_path(str(video.source_url), local_path)
            # ✅ S3 업로드 / Source upsert
            with open(local_path, "rb") as f:
                s3_key = upload_file_to_s3(
                    f,
                    f"raw/{video_id}.mp4",
                    content_type="video/mp4",
                )
        with CRUDVideo.atomic(db):
            CRUDVideo.update_status(db, video_id, VideoStatus.PENDING)
            CRUDSource.create(
                db,
                Source(
                    video_id=video_id,
                    s3_path=s3_key,
                ),
            )
