import uuid

from models.alert import AlertBase
from pydantic import BaseModel

__all__ = ["AlertRequest", "AlertResponse"]


class AlertRequest(BaseModel):
    result_id: uuid.UUID

class AlertResponse(AlertBase):
    alert_id: int
    points_added: int
    total_points: int | None
