from __future__ import annotations

import json
from typing import Any

from app.core.redis import redis_client


async def redis_get_json(key: str) -> dict[str, Any] | None:
    value = await redis_client.client.get(key)
    if not value:
        return None
    return json.loads(value)


async def redis_set_json(key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    await redis_client.client.set(key, json.dumps(payload), ex=ttl_seconds)
