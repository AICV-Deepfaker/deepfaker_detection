from fastapi import APIRouter, WebSocket

from ddp_backend.core.websocket import connection_context

router = APIRouter(prefix="/ws")


@router.websocket("/{user_id}")
async def user_websocket(websocket: WebSocket, user_id: int):
    async with connection_context(user_id, websocket):
        while True:
            await websocket.receive_text()
