"""Company-brain cache — the expensive RAG/LLM company analysis is built once
per ``(org_id, job_role)`` and shared across sessions instead of being
recomputed every time a session starts.

The cache returns deep copies so a session can never mutate a shared entry.
Entries expire after ``TTL_SECONDS``; ``invalidate_company_brain`` clears a
specific key, every entry of one organization, or the whole cache when
organization documents are refreshed.
Builds whose RAG retrieval returned nothing are never cached, so a session
re-tries retrieval instead of serving a stale fallback for the TTL window.
"""
import copy
import logging
import time
from threading import Lock
from typing import Optional

from app.intelligence.company_intelligence_builder import build_company_brain

logger = logging.getLogger(__name__)

TTL_SECONDS = 24 * 3600

_cache: dict[tuple, tuple[float, dict]] = {}
_lock = Lock()


def _key(scope_id, job_role: str) -> tuple:
    return (str(scope_id) if scope_id is not None else None, job_role or "")


async def get_or_build_company_brain(
    *,
    org_id: Optional[str] = None,
    department_id: Optional[int] = None,
    job_role: str = "",
    use_rag: bool = True,
    use_llm: bool = True,
    builder=None,
    ttl: float = TTL_SECONDS,
) -> dict:
    """Return the cached company brain for ``(org_id, job_role)``, building and
    caching it on a miss. Always returns a fresh deep copy. ``department_id`` is
    a deprecated alias for ``org_id``."""
    scope_id = org_id if org_id is not None else department_id
    key = _key(scope_id, job_role)
    now = time.monotonic()
    with _lock:
        entry = _cache.get(key)
        if entry is not None and now - entry[0] < ttl:
            return copy.deepcopy(entry[1])

    build_fn = builder or build_company_brain
    brain = await build_fn(
        org_id=org_id,
        department_id=department_id,
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
    else:
        logger.warning(
            "Company brain not cached for %s: retrieval returned no documents "
            "(reason=%s) — the next session will retry.",
            key,
            rag.get("reason", "unknown"),
        )
    return copy.deepcopy(brain)


def invalidate_company_brain(
    department_id: Optional[int] = None,
    job_role: Optional[str] = None,
    org_id: Optional[str] = None,
) -> None:
    """Evict cached company brains.

    - ``org_id`` alone evicts every job role cached for that organization (use
      this when its documents change);
    - ``org_id`` + ``job_role`` evicts one entry;
    - no arguments clears the whole cache. ``department_id`` is a deprecated
      alias for ``org_id``.
    """
    scope_id = org_id if org_id is not None else department_id
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
