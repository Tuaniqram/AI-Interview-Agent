"""Results of work whose input really does repeat, shared by all workers.

Keys are ``aura:cache:{kind}:{sha256 of the input}``, so the input itself (a CV, a listing, a
document) never appears in a key, and every entry has a TTL. Without Redis, or with the LLM cache
switch off (``get_llm_service()._cache_enabled = False``, used by the simulator), every lookup
misses and the work is simply done again.

TTLs are short for anything derived from a candidate's CV (it is personal data).
"""
import hashlib
import json
import logging
from typing import Any

from app.services.redis_client import AsyncLink, Breaker, create_sync_client

logger = logging.getLogger(__name__)

PREFIX = "aura:cache:"
CANDIDATE_TTL_S = 24 * 3600
ORG_TTL_S = 7 * 24 * 3600

_link = AsyncLink("content cache")
_sync_client = None
_sync_breaker = Breaker("content cache")


def enabled() -> bool:
    from app.services.llm_service import get_llm_service

    return getattr(get_llm_service(), "_cache_enabled", True)


def key(kind: str, *parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str, ensure_ascii=False)
    return f"{PREFIX}{kind}:{hashlib.sha256(payload.encode('utf-8', 'replace')).hexdigest()}"


def _log(cache_key: str, hit: bool) -> None:
    logger.info("cache %s %s", "hit" if hit else "miss", cache_key.rsplit(":", 1)[0])


async def get(cache_key: str) -> Any:
    """The cached value, or None."""
    client = _link.client() if enabled() else None
    if client is None:
        return None
    try:
        raw = await client.get(cache_key)
        _log(cache_key, raw is not None)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:  # noqa: BLE001 - a cache never breaks the work
        _link.failed(exc)
        return None


async def put(cache_key: str, value: Any, ttl: int) -> None:
    client = _link.client() if enabled() else None
    if client is None:
        return
    try:
        await client.set(cache_key, json.dumps(value, default=str), ex=ttl)
    except Exception as exc:  # noqa: BLE001
        _link.failed(exc)


def sync_client():
    """Blocking client for code that already runs in a worker thread (document ingestion)."""
    global _sync_client
    if _sync_client is None:
        _sync_client = create_sync_client()
    return _sync_client if _sync_breaker.allows() else None


def get_many_sync(keys: list[str]) -> list[Any]:
    client = sync_client() if keys and enabled() else None
    if client is None:
        return [None] * len(keys)
    try:
        values = [json.loads(v) if v is not None else None for v in client.mget(keys)]
        hits = sum(v is not None for v in values)
        logger.info("cache %d hit(s), %d miss(es) %s", hits, len(keys) - hits, keys[0].rsplit(":", 1)[0])
        return values
    except Exception as exc:  # noqa: BLE001
        _sync_breaker.failed(exc)
        return [None] * len(keys)


def put_many_sync(entries: dict[str, Any], ttl: int) -> None:
    client = sync_client() if entries and enabled() else None
    if client is None:
        return
    try:
        pipe = client.pipeline(transaction=False)
        for cache_key, value in entries.items():
            pipe.set(cache_key, json.dumps(value), ex=ttl)
        pipe.execute()
    except Exception as exc:  # noqa: BLE001
        _sync_breaker.failed(exc)
