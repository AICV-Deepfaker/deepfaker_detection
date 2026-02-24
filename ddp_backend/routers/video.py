from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from ddp_backend.core.database import get_db
from ddp_backend.core.s3 import upload_file_to_s3
from ddp_backend.core.security import get_current_user
from ddp_backend.models.models import Source, User, Video
from ddp_backend.schemas.enums import OriginPath, VideoStatus
from ddp_backend.task.video_processing import (
    process_uploaded_video,
    process_youtube_video,
)

router = APIRouter(prefix="/videos", tags=["videos"])


class LinkRequest(BaseModel):
    url: HttpUrl


@router.post("/upload")
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.user_id

    # 1) videos 생성
    video = Video(user_id=user_id, origin_path=OriginPath.UPLOAD, source_url=None)
    db.add(video)
    db.flush()  # video_id 확보

    # 2) S3 업로드 (raw/{video_id}_{uuid}.mp4)
    ext = Path(file.filename).suffix if file.filename else ".mp4"
    s3_key = f"raw/{video.video_id}_{uuid.uuid4().hex}{ext}"

    s3_key = upload_file_to_s3(
        file.file,
        s3_key,
        content_type=file.content_type or "video/mp4",
    )

    # 3) sources upsert(이 경우 신규)
    src = Source(video_id=video.video_id, s3_path=s3_key)
    db.add(src)

    # 4) 상태 pending
    video.status = VideoStatus.PENDING
    db.commit()

    # 5) BG 처리 시작
    background_tasks.add_task(process_uploaded_video, video.video_id)

    return {"video_id": video.video_id, "s3_path": s3_key, "queued": True}


@router.post("/link")
def link_video(
    payload: LinkRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.user_id

    video = Video(user_id=user_id, origin_path=OriginPath.LINK, source_url=str(payload.url))
    db.add(video)
    db.commit()
    db.refresh(video)

    # ✅ 업로드랑 동일하게 pending으로 명시 (일관성 + 디버깅 쉬움)
    video.status = VideoStatus.PENDING
    db.commit()

    background_tasks.add_task(process_youtube_video, video.video_id)
    return {"video_id": video.video_id, "queued": True}