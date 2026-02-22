"""
Alert CRUD
"""

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Alert

__all__ = [
    "AlertCreate",
    "CRUDAlert",
]


class AlertCreate(BaseModel):
    user_id: int
    result_id: int


class CRUDAlert:
    # 사용 : 신고하기
    @staticmethod
    def create(db: Session, alert_info: AlertCreate):
        """신고 생성"""
        db_alert = Alert(user_id=alert_info.user_id, result_id=alert_info.result_id)
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        return db_alert

    # 사용 : 신고 내역
    @staticmethod
    def get_by_user(db: Session, user_id: int):
        """유저의 신고 내역 조회"""
        query = select(Alert).where(Alert.alert_id == user_id)
        return db.scalars(query).all()
