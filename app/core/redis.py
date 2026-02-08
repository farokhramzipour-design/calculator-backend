from __future__ import annotations

import redis.asyncio as redis

from app.core.config import get_settings


class RedisClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = redis.from_url(settings.redis_url, decode_responses=True)

    @property
    def client(self) -> redis.Redis:
        return self._client


redis_client = RedisClient()
