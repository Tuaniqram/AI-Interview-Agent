"""Company-brain cache — the expensive RAG/LLM company analysis is built once
per ``(org_id, job_role)`` and shared across sessions instead of being
recomputed every time a session starts.

The cache returns deep copies so a session can never mutate a shared entry.
Entries expire after ``TTL_SECONDS``; ``invalidate_company_brain`` clears a
specific key, every entry of one organization, or the whole cache when
organization documents are refreshed.
Builds whose RAG retrieval returned nothing are never cached, so a session
re-tries retrieval instead of serving a stale fallback for the TTL window.

With Redis the entries are shared by all workers (``aura:cache:company:``) and invalidation is a
per-organization generation number in the key, so every worker stops using an old brain at once.
Without Redis each process keeps its own copy, and only the one that handled the upload forgets it.
"""
import copy
import hashlib
import json
import logging
import time
from threading import Lock
from typing import Optional

from app.intelligence.company_intelligence_builder import build_company_brain
from app.services.redis_client import AsyncLink, create_sync_client

logger = logging.getLogger(__name__)

TTL_SECONDS = 24 * 3600

_cache: dict[tuple, tuple[float, dict]] = {}

PREFIX = "aura:cache:company"
GENERATION_TTL_S = 2 * TTL_SECONDS  # outlives every entry made under it
_link = AsyncLink("company brain cache")


async def _shared_get(scope_id, job_role: str) -> tuple[Optional[str], Optional[dict]]:
    """``(key to write under, cached brain)``; ``(None, None)`` when Redis cannot be used."""
    client = _link.client()
    if client is None:
        return None, None
    try:
        generation = await client.get(f"{PREFIX}gen:{scope_id}") or "0"
        role = hashlib.sha256((job_role or "").encode("utf-8")).hexdigest()[:24]
        key = f"{PREFIX}:{scope_id}:{generation}:{role}"
        raw = await client.get(key)
        return key, json.loads(raw) if raw is not None else None
    except Exception as exc:  # noqa: BLE001
        _link.failed(exc)
        return None, None
_lock = Lock()


def _key(scope_id, job_role: str) -> tuple:
    return (str(scope_id) if scope_id is not None else None, job_role or "")


async def get_or_build_company_brain(
    *,
    org_id: Optional[str] = None,
    job_role: str = "",
    use_rag: bool = True,
    use_llm: bool = True,
    builder=None,
    ttl: float = TTL_SECONDS,
) -> dict:
    """Return the cached company brain for ``(org_id, job_role)``, building and
    caching it on a miss. Always returns a fresh deep copy."""
    key = _key(org_id, job_role)
    now = time.monotonic()
    shared_key, shared = await _shared_get(key[0], key[1])
    if shared is not None:
        return shared
    if shared_key is None:  # no Redis: this process's own copy
        with _lock:
            entry = _cache.get(key)
            if entry is not None and now - entry[0] < ttl:
                return copy.deepcopy(entry[1])

    build_fn = builder or build_company_brain
    brain = await build_fn(
        org_id=org_id,
        job_role=job_role,
        use_rag=use_rag,
        use_llm=use_llm,
    )

    # Only cache a successful build. A failed/empty RAG retrieval (e.g. docs
    # not yet indexed, or a slow embedding warm-up) must not be served to the
    # next session for up to 24h — sessions should re-try the retrieval until
    # it actually works.
    rag = brain.get("rag_metadata") or {}
    if rag.get("success", False) or rag.get("documents_retrieved", 0) > 0:
        with _lock:
            _cache[key] = (now, brain)
        if shared_key is not None:
            try:
                await _link.client().set(shared_key, json.dumps(brain, default=str), ex=int(ttl))
            except Exception as exc:  # noqa: BLE001
                _link.failed(exc)
    else:
        logger.warning(
            "Company brain not cached for %s: retrieval returned no documents "
            "(reason=%s) — the next session will retry.",
            key,
            rag.get("reason", "unknown"),
        )
    return copy.deepcopy(brain)


def invalidate_company_brain(
    job_role: Optional[str] = None,
    org_id: Optional[str] = None,
) -> None:
    """Evict cached company brains.

    - ``org_id`` alone evicts every job role cached for that organization (use
      this when its documents change);
    - ``org_id`` + ``job_role`` evicts one entry;
    - no arguments clears the whole cache.
    """
    scope_id = org_id
    if scope_id is not None:
        _invalidate_shared(str(scope_id))
    with _lock:
        if scope_id is None and job_role is None:
            _cache.clear()
            return
        if job_role is None:
            scope = str(scope_id)
            for key in [k for k in _cache if k[0] == scope]:
                _cache.pop(key, None)
            return
        _cache.pop(_key(scope_id, job_role), None)


def _invalidate_shared(scope_id: str) -> None:
    """Every worker's view of the organization is dropped (blocking: call from a worker thread)."""
    try:
        client = create_sync_client()
        if client is None:
            return
        with client:
            pipe = client.pipeline()
            pipe.incr(f"{PREFIX}gen:{scope_id}")
            pipe.expire(f"{PREFIX}gen:{scope_id}", GENERATION_TTL_S)
            pipe.execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Company brain invalidation could not reach Redis: %s", exc)
