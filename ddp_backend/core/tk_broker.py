from uuid import UUID

from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker
import taskiq_fastapi
from .config import REDIS_URL

from taskiq_redis import RedisStreamBroker

REDIS_URL = "redis://127.0.0.1:6379/0"
result_backend = RedisAsyncResultBackend[UUID | None](REDIS_URL)
broker = RedisStreamBroker(REDIS_URL).with_result_backend(result_backend)

taskiq_fastapi.init(broker, "ddp_backend.main:app")
