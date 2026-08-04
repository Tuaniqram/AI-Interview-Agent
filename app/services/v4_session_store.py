"""v4 interview session store.

Two interchangeable backends expose the same interface so the rest of the
codebase is unaffected by the selection:

* ``MemoryV4SessionStore`` — in-process dict with write-behind to Postgres
  (``v4_session_state``). Used when ``SESSION_STORE_BACKEND`` is unset or
  ``memory``. Falls back to a JSON file when no DATABASE_URL is configured.
* ``RedisV4SessionStore`` — Redis (``aura:sess:{id}``, TTL 24h) as the hot,
  shared tier, with Postgres ``v4_session_state`` as the durable checkpoint.
  Used when ``SESSION_STORE_BACKEND=redis``. Degrades to an in-process dict
  if Redis is unavailable so the interview never hard-fails.

``SESSION_STORE_BACKEND`` defaults to ``memory`` (no deploy change required
to stay on the existing behavior). Redis connections use the same
``REDIS_URL`` as ``app.services.cache`` (async); here we use the sync client.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Set
from uuid import uuid4

from app.graph.interview_state import InterviewState
from app.exceptions import SessionNotFoundException

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "v4_sessions.json",
)

SESSION_TTL_SECONDS = 24 * 3600
REDIS_KEY_PREFIX = "aura:sess:"


# ---------------------------------------------------------------------------
# Shared persistence helpers (Postgres v4_session_state, used by both tiers)
# ---------------------------------------------------------------------------

def _json_serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def _state_to_json(state: InterviewState) -> str:
    return json.dumps(state, default=_json_serialize)


def _state_from_json(state_json: str) -> InterviewState:
    return json.loads(state_json)


# ---------------------------------------------------------------------------
# Backend: in-memory + write-behind to Postgres (default / fallback)
# ---------------------------------------------------------------------------

class MemoryV4SessionStore:
    """In-process dict with write-behind persistence to Postgres.

    Persists to PostgreSQL (``v4_session_state`` table) or JSON file fallback.
    Survives server restarts when a DB is configured (sessions are loaded from
    DB on init). Use when ``SESSION_STORE_BACKEND`` is ``memory`` (default) or
    when Redis is unreachable at runtime.
    """

    def __init__(self, db_path: str | None = None, max_age_hours: int = 24):
        self._sessions: dict[str, InterviewState] = {}
        self._db_path = db_path or DEFAULT_DB_PATH
        self._dirty: Set[str] = set()
        self._sync_engine = self._create_sync_engine()
        if self._sync_engine:
            self._load_from_db()
        else:
            self._load_from_disk()
        self._evict_old(max_age_hours)

    def get(self, session_id: str) -> InterviewState | None:
        return self._sessions.get(session_id)

    def get_or_raise(self, session_id: str) -> InterviewState:
        state = self._sessions.get(session_id)
        if not state:
            raise SessionNotFoundException(session_id)
        return state

    def set(self, session_id: str, state: InterviewState) -> None:
        self._sessions[session_id] = state
        self._dirty.add(session_id)

    def pop(self, session_id: str) -> InterviewState | None:
        self._dirty.discard(session_id)
        state = self._sessions.pop(session_id, None)
        if state and self._sync_engine:
            try:
                self._delete_from_db(session_id)
            except Exception as e:
                logger.warning(f"Failed to delete v4 session {session_id} from DB: {e}")
        return state

    def list_active(self) -> list[dict]:
        return [
            {
                "session_id": sid,
                "started_at": str(s.get("start_time", "")),
                "question_number": s.get("question_number", 0),
                "job_role": s.get("job_role", ""),
            }
            for sid, s in self._sessions.items()
        ]

    def count(self) -> int:
        return len(self._sessions)

    def flush(self) -> None:
        if not self._dirty:
            return
        if self._sync_engine:
            self._save_to_db()
        else:
            self._save_to_disk()
        self._dirty.clear()

    def checkpoint(self, session_id: str, state: InterviewState) -> None:
        """Durable write-through of a single session (closes crash-loss gap).

        Replaces reliance on the shutdown-only ``flush()``. Also works on a
        Redis backend (which delegates the durable tier here).
        """
        if not self._sync_engine:
            self._save_to_disk()
            return
        try:
            self._upsert_db(session_id, state)
        except Exception as e:
            logger.warning(f"Failed to checkpoint v4 session {session_id}: {e}")

    # --- DB persistence ---

    def _create_sync_engine(self):
        raw_url = os.environ.get("DATABASE_URL", "")
        if not raw_url:
            return None
        try:
            from sqlalchemy import create_engine

            sync_url = raw_url.replace("+asyncpg", "").replace("+psycopg", "")
            return create_engine(sync_url, pool_pre_ping=True, pool_size=2, max_overflow=2)
        except ImportError:
            logger.warning("sqlalchemy not available — falling back to file persistence")
            return None
        except Exception as e:
            logger.warning(f"Failed to create sync engine: {e} — falling back to file")
            return None

    def _load_from_db(self) -> None:
        try:
            with self._sync_engine.connect() as conn:
                rows = conn.execute(
                    __import__("sqlalchemy").text(
                        "SELECT session_id::text, state::text FROM v4_session_state"
                    )
                ).fetchall()
            for sid_str, state_json in rows:
                self._sessions[sid_str] = json.loads(state_json)
            logger.info(f"Loaded {len(self._sessions)} v4 sessions from DB")
        except Exception as e:
            logger.warning(f"Failed to load v4 sessions from DB: {e} — trying file")
            self._load_from_disk()

    def _upsert_db(self, session_id: str, state: InterviewState) -> None:
        from sqlalchemy import text

        stmt = text("""
            INSERT INTO v4_session_state (session_id, state, state_version, updated_at)
            VALUES (:sid, CAST(:state AS jsonb), :version, now())
            ON CONFLICT (session_id)
            DO UPDATE SET state = EXCLUDED.state,
                          state_version = EXCLUDED.state_version,
                          updated_at = now()
        """)
        with self._sync_engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "sid": session_id,
                    "state": _state_to_json(state),
                    "version": int(state.get("state_version", 0)) + 1,
                },
            )

    def _save_to_db(self) -> None:
        from sqlalchemy import text

        stmt = text("""
            INSERT INTO v4_session_state (session_id, state, updated_at)
            VALUES (:sid, CAST(:state AS jsonb), now())
            ON CONFLICT (session_id)
            DO UPDATE SET state = EXCLUDED.state, updated_at = now()
        """)
        with self._sync_engine.begin() as conn:
            for sid in list(self._dirty):
                state = self._sessions.get(sid)
                if state:
                    conn.execute(
                        stmt, {"sid": sid, "state": _state_to_json(state)}
                    )

    def _delete_from_db(self, session_id: str) -> None:
        from sqlalchemy import text

        with self._sync_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM v4_session_state WHERE session_id = :sid"),
                {"session_id": session_id},
            )

    def _evict_old(self, max_age_hours: int = 24) -> int:
        evicted = 0
        if self._sync_engine:
            try:
                from sqlalchemy import text

                with self._sync_engine.begin() as conn:
                    result = conn.execute(
                        text(
                            "DELETE FROM v4_session_state "
                            "WHERE updated_at < now() - make_interval(hours => :hours)"
                        ),
                        {"hours": max_age_hours},
                    )
                    evicted = result.rowcount
            except Exception as e:
                logger.warning(f"Failed to evict stale sessions from DB: {e}")
        now = datetime.now(timezone.utc)
        to_remove = []
        for sid, s in self._sessions.items():
            start = s.get("start_time")
            if start:
                try:
                    if isinstance(start, str):
                        start_dt = datetime.fromisoformat(start)
                    else:
                        start_dt = start
                    if (now - start_dt).total_seconds() > max_age_hours * 3600:
                        to_remove.append(sid)
                except Exception:
                    continue
        for sid in to_remove:
            self._sessions.pop(sid, None)
        evicted += len(to_remove)
        if evicted:
            self._dirty.update(to_remove)
            logger.info(f"Evicted {evicted} stale v4 sessions (>{max_age_hours}h old)")
        return evicted

    # --- file persistence fallback ---

    def _save_to_disk(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            with open(self._db_path, "w", encoding="utf-8") as f:
                json.dump(self._sessions, f, default=_json_serialize, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save v4 sessions to disk: {e}")

    def _load_from_disk(self) -> None:
        try:
            if os.path.exists(self._db_path):
                with open(self._db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._sessions.update(data)
                logger.info(f"Loaded {len(data)} v4 sessions from {self._db_path}")
        except Exception as e:
            logger.warning(f"Failed to load v4 sessions from disk: {e}")


# ---------------------------------------------------------------------------
# Backend: Redis hot tier + Postgres durable checkpoint
# ---------------------------------------------------------------------------

class RedisV4SessionStore:
    """Redis as the shared hot tier, Postgres ``v4_session_state`` as durable
    checkpoint. Lazily hydrates a session from Postgres on miss so resume works
    across replicas. Degrades to an in-process dict (mirroring
    ``MemoryV4SessionStore`` semantics) if Redis is unavailable — the
    interview pipeline never observes a store failure.
    """

    def __init__(self, redis_client=None, sync_engine=None):
        # ``redis_client`` / ``sync_engine`` are injection points for tests;
        # when omitted, the real Redis/DATABASE_URL wiring is used.
        self._client = redis_client
        self._degraded: dict[str, InterviewState] = {}
        self._sync_engine = sync_engine if sync_engine is not None else self._create_sync_engine()
        if redis_client is None:
            self._init_client()
        else:
            self._enabled = True

    def _init_client(self):
        raw_url = os.environ.get("REDIS_URL", "")
        if not raw_url:
            logger.info("REDIS_URL not set — v4 session store in degraded memory mode")
            self._enabled = False
            return
        try:
            from redis import Redis

            self._client = Redis.from_url(raw_url, decode_responses=True)
            self._client.ping()
            self._enabled = True
            logger.info("Redis v4 session store connected")
        except Exception as e:
            logger.warning(f"Redis unavailable, session store degraded to memory: {e}")
            self._client = None
            self._enabled = False

    # -- shared Postgres helpers (checkpoint / lazy hydrate / pop-delete) --

    def _create_sync_engine(self):
        raw_url = os.environ.get("DATABASE_URL", "")
        if not raw_url:
            return None
        try:
            from sqlalchemy import create_engine

            sync_url = raw_url.replace("+asyncpg", "").replace("+psycopg", "")
            return create_engine(sync_url, pool_pre_ping=True, pool_size=2, max_overflow=2)
        except Exception:
            return None

    def _load_from_db(self, session_id: str) -> InterviewState | None:
        if not self._sync_engine:
            return None
        try:
            from sqlalchemy import text

            with self._sync_engine.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT state::text FROM v4_session_state WHERE session_id = :sid"
                    ),
                    {"sid": session_id},
                ).fetchone()
            if row is not None:
                return _state_from_json(row[0])
        except Exception as e:
            logger.warning(f"Failed to hydrate session {session_id} from DB: {e}")
        return None

    def _upsert_db(self, session_id: str, state: InterviewState) -> None:
        if not self._sync_engine:
            return
        try:
            from sqlalchemy import text

            stmt = text("""
                INSERT INTO v4_session_state (session_id, state, state_version, updated_at)
                VALUES (:sid, CAST(:state AS jsonb), :version, now())
                ON CONFLICT (session_id)
                DO UPDATE SET state = EXCLUDED.state,
                              state_version = EXCLUDED.state_version,
                              updated_at = now()
            """)
            with self._sync_engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "sid": session_id,
                        "state": _state_to_json(state),
                        "version": int(state.get("state_version", 0)) + 1,
                    },
                )
        except Exception as e:
            logger.warning(f"Failed to checkpoint session {session_id} to DB: {e}")

    def _delete_from_db(self, session_id: str) -> None:
        if not self._sync_engine:
            return
        try:
            from sqlalchemy import text

            with self._sync_engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM v4_session_state WHERE session_id = :sid"),
                    {"sid": session_id},
                )
        except Exception as e:
            logger.warning(f"Failed to delete v4 session {session_id} from DB: {e}")

    # -- public interface (identical to MemoryV4SessionStore) --

    def get(self, session_id: str) -> InterviewState | None:
        if self._enabled:
            try:
                raw = self._client.get(self._key(session_id))
                if raw is not None:
                    return _state_from_json(raw)
            except Exception as e:
                logger.warning(f"Redis get failed for {session_id}: {e}")
                # fall through to lazy DB hydrate + degraded dict
        state = self._degraded.get(session_id)
        if state is None:
            state = self._load_from_db(session_id)
            if state is not None:
                self._degraded[session_id] = state
        return state

    def get_or_raise(self, session_id: str) -> InterviewState:
        state = self.get(session_id)
        if not state:
            raise SessionNotFoundException(session_id)
        return state

    def set(self, session_id: str, state: InterviewState) -> None:
        if self._enabled:
            try:
                self._client.setex(
                    self._key(session_id),
                    SESSION_TTL_SECONDS,
                    _state_to_json(state),
                )
                return
            except Exception as e:
                logger.warning(f"Redis set failed for {session_id}: {e}")
        self._degraded[session_id] = state

    def pop(self, session_id: str) -> InterviewState | None:
        state = self._degraded.pop(session_id, None)
        if state is None and self._enabled:
            try:
                raw = self._client.get(self._key(session_id))
                if raw is not None:
                    state = _state_from_json(raw)
            except Exception as e:
                logger.warning(f"Redis pop failed for {session_id}: {e}")
        if self._enabled:
            try:
                self._client.delete(self._key(session_id))
            except Exception as e:
                logger.warning(f"Redis delete failed for {session_id}: {e}")
        if state is not None:
            self._delete_from_db(session_id)
        return state

    def list_active(self) -> list[dict]:
        if not self._enabled:
            return [
                {
                    "session_id": sid,
                    "started_at": str(s.get("start_time", "")),
                    "question_number": s.get("question_number", 0),
                    "job_role": s.get("job_role", ""),
                }
                for sid, s in self._degraded.items()
            ]
        out: list[dict] = []
        try:
            cur = self._client
            for key in cur.scan_iter(f"{REDIS_KEY_PREFIX}*"):
                try:
                    raw = cur.get(key)
                    if raw is None:
                        continue
                    s = _state_from_json(raw)
                    sid = key.removeprefix(REDIS_KEY_PREFIX)
                    out.append(
                        {
                            "session_id": sid,
                            "started_at": str(s.get("start_time", "")),
                            "question_number": s.get("question_number", 0),
                            "job_role": s.get("job_role", ""),
                        }
                    )
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Redis scan failed for list_active: {e}")
        return out

    def count(self) -> int:
        if not self._enabled:
            return len(self._degraded)
        try:
            return int(self._client.dbsize())
        except Exception as e:
            logger.warning(f"Redis dbsize failed: {e}")
            return len(self._degraded)

    def flush(self) -> None:
        # Redis is already durable per-key (TTL); flush here is a no-op that
        # also drains any in-memory degraded entries to Postgres as a safety net.
        for sid, state in list(self._degraded.items()):
            self._upsert_db(sid, state)
        self._degraded.clear()

    def checkpoint(self, session_id: str, state: InterviewState) -> None:
        """Force a durable write to Postgres (used on turn completion)."""
        self._upsert_db(session_id, state)

    def _key(self, session_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}{session_id}"

    def close(self) -> None:
        """Close the Redis client (called at app shutdown). No-op for memory."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Redis close failed: {e}")
            self._enabled = False

    async def aclose(self) -> None:
        """Async close wrapper (kept for lifespans that await cleanup)."""
        self.close()


# Backward-compat alias so any external code referencing the old name still works.
V4SessionStore = MemoryV4SessionStore


_STORE: "V4SessionStore | RedisV4SessionStore | None" = None


def get_v4_session_store() -> V4SessionStore:
    global _STORE
    if _STORE is None:
        backend = os.environ.get("SESSION_STORE_BACKEND", "memory").strip().lower()
        if backend == "redis":
            _STORE = RedisV4SessionStore()
        else:
            _STORE = MemoryV4SessionStore()
    return _STORE
