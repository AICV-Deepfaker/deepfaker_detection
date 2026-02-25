from uuim import UUID

from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker
import taskiq_fastapi
from .config import REDIS_URL

result_backend = RedisAsyncResultBackend[UUID | None](REDIS_URL)
broker = ListQueueBroker(REDIS_URL).with_result_backend(result_backend)

taskiq_fastapi.init(broker, "ddp_backend.main:app")