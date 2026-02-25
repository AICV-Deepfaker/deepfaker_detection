"""
Source CRUD
"""

from uuid import UUID
from sqlmodel import select
from sqlmodel.orm.session import Session

from ddp_backend.models import Source

from .base import CRUDBase

__all__ = [
    "CRUDSource",
]

class CRUDSource(CRUDBase):
    # 사용 : s3 업로드 후 video_id와 함께 저장
    @classmethod
    def create(cls, db: Session, db_source: Source):
        """S3 경로 저장"""
        db_source = Source(
            video_id=db_source.video_id,
            s3_path=db_source.s3_path,
        )
        db.add(db_source)
        cls.commit_or_flush(db)
        db.refresh(db_source)
        return db_source

    # 사용 : 영상 재호출(분석 실패 시)
    @classmethod
    def get_by_video(cls, db: Session, video_id: UUID):
        """video_id로 S3 경로 조회"""
        query = select(Source).where(Source.video_id == video_id)
        return db.scalars(query).one_or_none()

    @classmethod
    def update_s3(cls, db: Session, video_id: UUID, s3_path: str):
        src = cls.get_by_video(db, video_id)
        if src is None:
            return None
        src.s3_path = s3_path

        cls.commit_or_flush(db)
        db.refresh(src)
        return src

    @classmethod
    def upsert_source(cls, db: Session, video_id: UUID, s3_path: str):
        src = cls.update_s3(db, video_id, s3_path)
        if src:
            return src
        return cls.create(db, Source(video_id=video_id, s3_path=s3_path))
        