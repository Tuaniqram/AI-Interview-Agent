import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter.

    Applies to a configurable set of path prefixes.  Tracks per-IP buckets.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_requests: int = 60,
        window_seconds: int = 60,
        paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.paths = paths or []
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable):
        if self.paths and not any(request.url.path.startswith(p) for p in self.paths):
            return await call_next(request)

        key = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self._buckets[key]
        bucket[:] = [t for t in bucket if now - t < self.window_seconds]

        if len(bucket) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )

        bucket.append(now)
        return await call_next(request)
