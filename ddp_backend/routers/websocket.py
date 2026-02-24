from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket

from ddp_backend.core.security import get_current_user
from ddp_backend.core.websocket import connection_context
from ddp_backend.models import User

router = APIRouter(prefix="/ws")


@router.websocket("/{user_id}")
async def user_websocket(
    websocket: WebSocket, user_id: uuid.UUID, user: Annotated[User, Depends(get_current_user)]
):
    if user_id != user.user_id:
        raise HTTPException(403, "Forbidden")
    async with connection_context(user_id, websocket):
        while True:
            await websocket.receive_text()
