from uuid import UUID

from pydantic import BaseModel

__all__ = ['WorkerResultMessage']

class WorkerResultMessage(BaseModel):
    user_id: UUID
    result_id: UUID
