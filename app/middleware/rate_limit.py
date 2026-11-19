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
        trusted_proxies: int = 0,
    ):
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.paths = paths or []
        # How many reverse proxies sit in front of this app. 0 (default) keys on the socket peer, which is the
        # proxy's own address behind one: every user then shares one bucket. With N > 0 the client is the Nth entry
        # from the RIGHT of X-Forwarded-For (what the proxy nearest to us saw); entries a caller put on the left are
        # ignored, so a forged header cannot pick its own bucket.
        self.trusted_proxies = max(0, trusted_proxies)
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._since_prune = 0

    def _client_key(self, scope: Scope) -> str:
        if self.trusted_proxies:
            for name, value in scope.get("headers", []):
                if name == b"x-forwarded-for":
                    hops = [h.strip() for h in value.decode("latin-1").split(",") if h.strip()]
                    if len(hops) >= self.trusted_proxies:
                        return hops[-self.trusted_proxies]
                    break  # header shorter than the proxy chain: do not trust it
        client = scope.get("client")
        return client[0] if client else "unknown"

    def _prune(self, now: float) -> None:
        """Drop addresses with no request inside the window, so the table cannot grow without bound."""
        for key in [k for k, ts in self._buckets.items() if not ts or now - ts[-1] >= self.window_seconds]:
            del self._buckets[key]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # websockets / lifespan pass straight through
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if self.paths and not any(path.startswith(p) for p in self.paths):
            await self.app(scope, receive, send)
            return

        key = self._client_key(scope)
        now = time.time()
        self._since_prune += 1
        if self._since_prune >= 1024:
            self._since_prune = 0
            self._prune(now)
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
