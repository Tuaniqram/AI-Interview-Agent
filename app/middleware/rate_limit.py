import time
from collections import defaultdict

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class RateLimitMiddleware:
    """Simple in-memory sliding-window rate limiter.

    Applies to a configurable set of path prefixes.  Tracks per-IP buckets.

    Implemented as a plain ASGI middleware (not ``BaseHTTPMiddleware``): the latter makes
    the client wait for FastAPI ``BackgroundTasks`` to finish before the response completes,
    which turned a ~1s apply request into 10s+ while the fit evaluation ran.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_requests: int = 60,
        window_seconds: int = 60,
        paths: list[str] | None = None,
    ):
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.paths = paths or []
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # websockets / lifespan pass straight through
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if self.paths and not any(path.startswith(p) for p in self.paths):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        key = client[0] if client else "unknown"
        now = time.time()
        bucket = self._buckets[key]
        bucket[:] = [t for t in bucket if now - t < self.window_seconds]

        if len(bucket) >= self.max_requests:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )
            await response(scope, receive, send)
            return

        bucket.append(now)
        await self.app(scope, receive, send)
