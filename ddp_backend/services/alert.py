from __future__ import annotations

from sqlalchemy.orm import Session

from ddp_backend.models.models import Alert, Result, User


ALERT_POINT = 1000  # 정책: 신고 1회 1000점


def create_alert(db: Session, user_id: int, result_id: int) -> dict:
    # result 존재 확인
    result = db.query(Result).filter(Result.result_id == result_id).first()
    if not result:
        raise ValueError("result_id not found")

    # 중복 신고 방지(같은 유저가 같은 result를 여러번 신고)
    exists = db.query(Alert).filter(Alert.user_id == user_id, Alert.result_id == result_id).first()
    if exists:
        raise ValueError("already reported")

    alert = Alert(user_id=user_id, result_id=result_id)
    db.add(alert)

    # 포인트 적립
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user.activation_points += ALERT_POINT

    db.commit()
    db.refresh(alert)

    return {
        "alert_id": alert.alert_id,
        "result_id": alert.result_id,
        "user_id": alert.user_id,
        "points_added": ALERT_POINT,
        "total_points": user.activation_points if user else None,
    }