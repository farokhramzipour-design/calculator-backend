from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential


@dataclass
class CircuitBreaker:
    max_failures: int = 3
    reset_seconds: int = 30
    failures: int = 0
    last_failure_ts: float | None = None

    def allow(self) -> bool:
        if self.failures < self.max_failures:
            return True
        if self.last_failure_ts is None:
            return True
        if time.time() - self.last_failure_ts > self.reset_seconds:
            self.failures = 0
            self.last_failure_ts = None
            return True
        return False

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_ts = time.time()

    def record_success(self) -> None:
        self.failures = 0
        self.last_failure_ts = None


async def get_json(url: str, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True,
        ):
            with attempt:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
    return {}
