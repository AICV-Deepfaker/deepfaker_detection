import asyncio
from typing import TypedDict, cast

from fastapi import FastAPI
from pydantic import ValidationError
from redis.asyncio import Redis

from ddp_backend.schemas.api import WorkerPubSubAPI

from .config import REDIS_URL
from .websocket import connection_manager

redis = Redis.from_url(REDIS_URL, decode_responses=True, db=1)
NOTIFY_CHANNEL = "analysis_notification"


class RedisMessage(TypedDict):
    type: str
    pattern: str | None
    channel: str
    data: str  # decode_responses=True 일 때 str


async def redis_connector(app: FastAPI):
    pubsub = redis.pubsub()
    await pubsub.subscribe(NOTIFY_CHANNEL)

    try:
        while True:
            async for message in pubsub.listen():
                msg = cast(RedisMessage, message)
                if msg["type"] != "message":
                    continue
                try:
                    data = WorkerPubSubAPI.model_validate_json(msg["data"])
                except ValidationError:
                    continue
                await connection_manager.send_message(data.user_id, data.result_id)
    except asyncio.CancelledError:
        await pubsub.unsubscribe()
        await redis.close()
