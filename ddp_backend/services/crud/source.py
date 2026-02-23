"""
Source CRUD
"""

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ddp_backend.models import Source

__all__ = [
    "SourceCreate",
    "CRUDSource",
]


class SourceCreate(BaseModel):
    video_id: int
    s3_path: str


class CRUDSource:
    # 사용 : s3 업로드 후 video_id와 함께 저장
    @staticmethod
    def create(db: Session, source_info: SourceCreate):
        """S3 경로 저장"""
        db_source = Source(
            video_id=source_info.video_id,
            s3_path=source_info.s3_path,
        )
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        return db_source

    # 사용 : 영상 재호출(분석 실패 시)
    @staticmethod
    def get_by_video(db: Session, video_id: int):
        """video_id로 S3 경로 조회"""
        query = select(Source).where(Source.video_id == video_id)
        return db.scalars(query).one_or_none()
