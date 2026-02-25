"""
Alert CRUD
"""

from uuid import UUID

from sqlmodel import select
from sqlmodel.orm.session import Session

from ddp_backend.models import Alert

from .base import CRUDBase

__all__ = [
    "CRUDAlert",
]


class CRUDAlert(CRUDBase):
    # 사용 : 신고하기
    @classmethod
    def create(cls, db: Session, db_alert: Alert):
        """신고 생성"""
        db.add(db_alert)
        cls.commit_or_flush(db)
        db.refresh(db_alert)
        return db_alert

    # 사용 : 신고 내역
    @classmethod
    def get_by_user(cls, db: Session, user_id: UUID):
        """유저의 신고 내역 조회"""
        query = select(Alert).where(Alert.user_id == user_id)
        return db.scalars(query).all()

    @classmethod
    def get_by_user_result(cls, db: Session, user_id: UUID, result_id: UUID):
        query = select(Alert).where(
            Alert.user_id == user_id, Alert.result_id == result_id
        )
        return db.scalars(query).first()
