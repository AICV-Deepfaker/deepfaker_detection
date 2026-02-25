from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.orm.session import Session

from ddp_backend.core.database import get_db
from ddp_backend.core.security import get_current_user
from ddp_backend.models import User
from ddp_backend.schemas.alert import AlertRequest

# from ddp_backend.services.dependencies import get_db, get_current_user
from ddp_backend.services.alert import create_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("")
def report_alert(
    payload: AlertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    신고 생성 + 포인트 적립
    """
    try:
        return create_alert(db=db, user_id=user.user_id, result_id=payload.result_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
