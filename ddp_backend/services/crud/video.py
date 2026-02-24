"""
Video CRUD
"""

from uuid import UUID
from sqlmodel import select
from sqlmodel.orm.session import Session

from ddp_backend.models import Video
from ddp_backend.schemas.enums import VideoStatus

__all__ = [
    "CRUDVideo",
]


class CRUDVideo:
    # 사용 : 비디오 url/업로드 입력
    @staticmethod
    def create(db: Session, db_video: Video):
        """비디오 생성"""
        db.add(db_video)
        db.commit()
        db.refresh(db_video)  # video_id 포함
        return db_video  # video_id가 채워진 객체 반환

    # def get_video_by_id(db: Session, video_id: int): # 필요시 주석 해제
    #     """ video_id로 비디오 조회 """
    #     return db.query(Video).filter(Video.video_id == video_id).first()

    # 사용 : 히스토리(url)
    @staticmethod
    def get_by_user(db: Session, user_id: UUID):
        """유저의 모든 비디오 조회"""
        query = select(Video).where(Video.user_id == user_id)
        return db.scalars(query).all()

    # 사용 : 영상 분석 상태 업로드
    @staticmethod
    def update_status(db: Session, video_id: UUID, status: VideoStatus):
        """비디오 상태 업데이트"""
        video = db.get(Video, video_id)  # video_id로 조회
        if video is None:
            return None

        video.status = status  # 상태 업로드 (pending, processing, completed, failed)
        db.commit()
        db.refresh(video)
        return video
