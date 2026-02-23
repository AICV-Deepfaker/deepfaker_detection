from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker
from .config import REDIS_URL

result_backend = RedisAsyncResultBackend[int | None](REDIS_URL)
broker = ListQueueBroker(REDIS_URL).with_result_backend(result_backend)
