from __future__ import annotations

import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, limit: int = 10, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: defaultdict[str, deque] = defaultdict(deque)

    def check(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.time()
        window = self.requests[key]
        while window and now - window[0] > self.window_seconds:
            window.popleft()
        if len(window) >= self.limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        window.append(now)


rate_limiter = RateLimiter()
