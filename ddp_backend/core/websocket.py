from contextlib import asynccontextmanager

from uuid import UUID
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.connections: dict[UUID, WebSocket] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.connections[user_id] = websocket

    def disconnect(self, user_id: UUID):
        if user_id in self.connections:
            del self.connections[user_id]

    async def send_message(self, user_id: UUID, res_id: UUID | None, error_msg: str | None = None):
        if user_id in self.connections:
            websocket = self.connections[user_id]
            await websocket.send_text(f"{res_id}" if res_id else f"{error_msg}")


connection_manager = ConnectionManager()


@asynccontextmanager
async def connection_context(user_id: UUID, websocket: WebSocket):
    try:
        await connection_manager.connect(user_id, websocket)
        yield
    finally:
        connection_manager.disconnect(user_id)
