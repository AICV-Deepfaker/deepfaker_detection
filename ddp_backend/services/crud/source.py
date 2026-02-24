"""
Source CRUD
"""

from uuid import UUID
from sqlmodel import select
from sqlmodel.orm.session import Session

from ddp_backend.models import Source

__all__ = [
    "CRUDSource",
]

class CRUDSource:
    # 사용 : s3 업로드 후 video_id와 함께 저장
    @staticmethod
    def create(db: Session, db_source: Source):
        """S3 경로 저장"""
        db_source = Source(
            video_id=db_source.video_id,
            s3_path=db_source.s3_path,
        )
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        return db_source

    # 사용 : 영상 재호출(분석 실패 시)
    @staticmethod
    def get_by_video(db: Session, video_id: UUID):
        """video_id로 S3 경로 조회"""
        query = select(Source).where(Source.video_id == video_id)
        return db.scalars(query).one_or_none()
