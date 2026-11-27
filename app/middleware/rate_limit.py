import hashlib
import time
import uuid
from collections import defaultdict

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.services.redis_client import AsyncLink

KEY_PREFIX = "aura:rl:"

# Sliding window shared by all workers. KEYS[1] = bucket; ARGV = now (ms), window (ms), limit, member.
# A rejected request is not added, so a client that keeps hammering recovers after one window.
_WINDOW_LUA = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1] - ARGV[2])
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[3]) then return 0 end
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
redis.call('PEXPIRE', KEYS[1], ARGV[2])
return 1
"""


class RateLimitMiddleware:
    """Sliding-window rate limiter shared by all workers through Redis.

    Applies to a configurable set of path prefixes.  Tracks per-IP buckets. Without Redis each
    process counts for itself (the limit is then per worker).

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
        name: str | None = None,
        redis_client=None,
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
        # Separate counters per limiter: the auth and the general limit must not share a bucket.
        self.name = name or f"{max_requests}-{window_seconds}"
        self._redis = AsyncLink("rate limiting", redis_client)

    async def _allow_shared(self, client_key: str) -> bool | None:
        """Redis verdict, or None when Redis cannot be asked."""
        client = self._redis.client()
        if client is None:
            return None
        digest = hashlib.sha256(client_key.encode("utf-8", "replace")).hexdigest()[:24]
        try:
            return bool(await client.eval(
                _WINDOW_LUA, 1, f"{KEY_PREFIX}{self.name}:{digest}",
                int(time.time() * 1000), self.window_seconds * 1000, self.max_requests, uuid.uuid4().hex,
            ))
        except Exception as exc:  # noqa: BLE001 - never fail a request because Redis is down
            self._redis.failed(exc)
            return None

    def _allow_local(self, key: str) -> bool:
        now = time.time()
        self._since_prune += 1
        if self._since_prune >= 1024:
            self._since_prune = 0
            self._prune(now)
        bucket = self._buckets[key]
        bucket[:] = [t for t in bucket if now - t < self.window_seconds]
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True

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
        allowed = await self._allow_shared(key)
        if allowed is None:
            allowed = self._allow_local(key)

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
