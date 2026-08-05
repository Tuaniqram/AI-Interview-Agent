"""Company-brain cache — the expensive RAG/LLM company analysis is built once
per ``(department_id, job_role)`` and shared across sessions instead of being
recomputed every time a session starts.

The cache returns deep copies so a session can never mutate a shared entry.
Entries expire after ``TTL_SECONDS``; ``invalidate_company_brain`` clears a
specific key (or the whole cache) when department documents are refreshed.
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


def _key(department_id: Optional[int], job_role: str) -> tuple:
    return (department_id, job_role or "")


async def get_or_build_company_brain(
    *,
    department_id: Optional[int] = None,
    job_role: str = "",
    use_rag: bool = True,
    use_llm: bool = True,
    builder=None,
    ttl: float = TTL_SECONDS,
) -> dict:
    """Return the cached company brain for ``(department_id, job_role)``,
    building and caching it on a miss. Always returns a fresh deep copy."""
    key = _key(department_id, job_role)
    now = time.monotonic()
    with _lock:
        entry = _cache.get(key)
        if entry is not None and now - entry[0] < ttl:
            return copy.deepcopy(entry[1])

    build_fn = builder or build_company_brain
    brain = await build_fn(
        department_id=department_id,
        job_role=job_role,
        use_rag=use_rag,
        use_llm=use_llm,
    )

    with _lock:
        _cache[key] = (now, brain)
    return copy.deepcopy(brain)


def invalidate_company_brain(
    department_id: Optional[int] = None,
    job_role: Optional[str] = None,
) -> None:
    """Evict a specific ``(department_id, job_role)`` entry (or all entries
    when neither argument is given)."""
    with _lock:
        if department_id is None and job_role is None:
            _cache.clear()
            return
        key = _key(department_id, job_role or "")
        _cache.pop(key, None)
