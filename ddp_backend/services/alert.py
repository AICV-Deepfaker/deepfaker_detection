from __future__ import annotations

import uuid

from sqlmodel.orm.session import Session
from sqlalchemy.exc import NoResultFound

from ddp_backend.models.models import Alert
from ddp_backend.services.crud import CRUDResult, CRUDAlert, CRUDUser
from ddp_backend.schemas.alert import AlertResponse

ALERT_POINT = 1000  # 정책: 신고 1회 1000점

def create_alert(db: Session, user_id: uuid.UUID, result_id: uuid.UUID) -> AlertResponse:
    # result 존재 확인
    result = CRUDResult.get_by_id(db, result_id)
    if not result:
        raise ValueError("result_id not found")

    if result.user_id != user_id:
        raise ValueError("Result is not by user")

    # 중복 신고 방지(같은 유저가 같은 result를 여러번 신고)
    exists = CRUDAlert.get_by_user_result(db, user_id, result_id)
    if exists:
        raise ValueError("already reported")


    with CRUDAlert.atomic(db):
        alert = CRUDAlert.create(db, Alert(user_id=user_id, result_id=result_id))
        assert alert.alert_id is not None

        # 포인트 적립
        point: int | None
        try:
            point = CRUDUser.update_active_points(db, user_id, ALERT_POINT)
        except NoResultFound:
            point = None

    return AlertResponse(
        alert_id=alert.alert_id,
        result_id=alert.result_id,
        user_id=alert.user_id,
        points_added=ALERT_POINT,
        total_points=point,
    )