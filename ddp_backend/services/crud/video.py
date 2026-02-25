"""
Video CRUD
"""

from uuid import UUID
from sqlmodel import select
from sqlmodel.orm.session import Session

from ddp_backend.models import Video
from ddp_backend.schemas.enums import VideoStatus

from .base import CRUDBase
__all__ = [
    "CRUDVideo",
]


class CRUDVideo(CRUDBase):
    # 사용 : 비디오 url/업로드 입력
    @classmethod
    def create(cls, db: Session, db_video: Video):
        """비디오 생성"""
        db.add(db_video)
        cls.commit_or_flush(db)
        db.refresh(db_video)  # video_id 포함
        return db_video  # video_id가 채워진 객체 반환

    @classmethod
    def get_by_id(cls, db: Session, video_id: UUID):
        return db.get(Video, video_id)

    # 사용 : 히스토리(url)
    @classmethod
    def get_by_user(cls, db: Session, user_id: UUID):
        """유저의 모든 비디오 조회"""
        query = select(Video).where(Video.user_id == user_id)
        return db.scalars(query).all()

    # 사용 : 영상 분석 상태 업로드
    @classmethod
    def update_status(cls, db: Session, video_id: UUID, status: VideoStatus):
        """비디오 상태 업데이트"""
        video = db.get(Video, video_id)  # video_id로 조회
        if video is None:
            return None

        video.status = status  # 상태 업로드 (pending, processing, completed, failed)
        cls.commit_or_flush(db)
        db.refresh(video)
        return video
