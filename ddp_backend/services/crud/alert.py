"""
Alert CRUD
"""

from uuid import UUID

from sqlmodel import select
from sqlmodel.orm.session import Session

from ddp_backend.models import Alert

__all__ = [
    "CRUDAlert",
]


class CRUDAlert:
    # 사용 : 신고하기
    @staticmethod
    def create(db: Session, db_alert: Alert, do_commit: bool = True):
        """신고 생성"""
        db.add(db_alert)
        if do_commit:
            db.commit()
            db.refresh(db_alert)
        return db_alert

    # 사용 : 신고 내역
    @staticmethod
    def get_by_user(db: Session, user_id: UUID):
        """유저의 신고 내역 조회"""
        query = select(Alert).where(Alert.user_id == user_id)
        return db.scalars(query).all()

    @staticmethod
    def get_by_user_result(db: Session, user_id: UUID, result_id: UUID):
        query = select(Alert).where(
            Alert.user_id == user_id, Alert.result_id == result_id
        )
        return db.scalars(query).first()
