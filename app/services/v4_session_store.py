"""v4 interview session store.

Two interchangeable backends expose the same interface so the rest of the
codebase is unaffected by the selection:

* ``MemoryV4SessionStore`` — in-process dict with write-behind to Postgres
  (``v4_session_state``). Used when ``SESSION_STORE_BACKEND`` is unset or
  ``memory``. Falls back to a JSON file when no DATABASE_URL is configured.
* ``RedisV4SessionStore`` — the production path, and the only one that is correct with more than one
  worker: Redis (``aura:sess:{id}``, TTL 24h) shared between workers with compare-and-set writes,
  Postgres ``v4_session_state`` as the durable source of truth.

The backend is ``SESSION_STORE_BACKEND`` (``redis`` / ``memory``); unset, it is Redis when
``REDIS_URL`` is set.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Set
from uuid import uuid4

from redis.exceptions import ResponseError

from app.core.interview_state import InterviewState
from app.exceptions import SessionNotFoundException, StaleSessionError
from app.services.redis_client import Breaker, create_sync_client, redis_url

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


def _version_of(state: InterviewState) -> int:
    return int(state.get("store_version") or 0)


def _summary(session_id: str, state: InterviewState) -> dict:
    return {
        "session_id": session_id,
        "started_at": str(state.get("start_time", "")),
        "question_number": state.get("question_number", 0),
        "job_role": state.get("job_role", ""),
    }


def _create_sync_engine():
    """Blocking SQLAlchemy engine for ``v4_session_state``, or None without DATABASE_URL."""
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        return None
    try:
        from sqlalchemy import create_engine

        sync_url = raw_url.replace("+asyncpg", "").replace("+psycopg", "")
        # Bounded connect: a wedged/slow remote pooler must fail fast.
        return create_engine(
            sync_url,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=4,
            connect_args={"connect_timeout": 3},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to create sync engine: {e}")
        return None


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
        # An explicit ``db_path`` marks a hermetic (test/local) store: file-backed
        # only, never Postgres. Only the default config (db_path=None) uses
        # DATABASE_URL, so unit tests never touch a live database.
        self._sync_engine = None if db_path is not None else _create_sync_engine()
        # NOTE: the Postgres store is deliberately NOT bulk-loaded at init.
        # Loading every v4_session_state row synchronously on the event loop
        # froze the server for minutes on a slow/remote database (single
        # session-start request blocked all traffic). Sessions hydrate lazily
        # per id on ``get`` miss instead.
        if not self._sync_engine:
            self._load_from_disk()

    def get(self, session_id: str) -> InterviewState | None:
        state = self._sessions.get(session_id)
        if state is None and self._sync_engine:
            state = self._hydrate_from_db(session_id)
            if state is not None:
                self._sessions[session_id] = state
        return state

    def _hydrate_from_db(self, session_id: str) -> InterviewState | None:
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

    def get_or_raise(self, session_id: str) -> InterviewState:
        state = self.get(session_id)
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
                {"sid": session_id},
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
# Durable tier used by the Redis backend
# ---------------------------------------------------------------------------

_VERSION_SQL = "COALESCE(CAST({column} ->> 'store_version' AS bigint), 0)"


class PostgresCheckpoint:
    """``v4_session_state`` as the durable source of truth.

    Errors are raised, not swallowed: the store decides what a failed read or write means.
    ``state_version`` holds the store version; comparisons read it from the JSON, so rows written
    before versions existed count as version 0.
    """

    def __init__(self, engine):
        self._engine = engine

    def load(self, session_id: str) -> InterviewState | None:
        return self.load_if_newer(session_id, -1)

    def load_if_newer(self, session_id: str, version: int) -> InterviewState | None:
        from sqlalchemy import text

        stmt = text(
            "SELECT CAST(state AS text) FROM v4_session_state "
            "WHERE session_id = :sid AND " + _VERSION_SQL.format(column="state") + " > :version"
        )
        with self._engine.connect() as conn:
            row = conn.execute(stmt, {"sid": session_id, "version": version}).fetchone()
        return _state_from_json(row[0]) if row is not None else None

    def upsert_if_newer(self, session_id: str, state: InterviewState, version: int) -> bool:
        """Write unless the row already holds this or a later version. False = refused.

        Writing the identical state again is accepted (a checkpoint repeats what ``set`` stored).
        """
        from sqlalchemy import text

        stmt = text(
            "INSERT INTO v4_session_state (session_id, state, state_version, updated_at) "
            "VALUES (:sid, CAST(:state AS jsonb), :version, now()) "
            "ON CONFLICT (session_id) DO UPDATE SET state = EXCLUDED.state, "
            "state_version = EXCLUDED.state_version, updated_at = now() "
            "WHERE " + _VERSION_SQL.format(column="v4_session_state.state") + " < :version "
            "OR v4_session_state.state = EXCLUDED.state"
        )
        with self._engine.begin() as conn:
            result = conn.execute(
                stmt, {"sid": session_id, "state": _state_to_json(state), "version": version}
            )
        return result.rowcount > 0

    def delete(self, session_id: str) -> None:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            conn.execute(
                text("DELETE FROM v4_session_state WHERE session_id = :sid"), {"sid": session_id}
            )


# ---------------------------------------------------------------------------
# Backend: Redis hot tier + Postgres durable checkpoint
# ---------------------------------------------------------------------------

# Compare-and-set. KEYS[1] = session key; ARGV = expected version, new version, state JSON, TTL.
# Refused only when Redis holds a LATER version than the writer read. A Redis copy that is behind
# (writes went to Postgres while Redis was unreachable) is simply overwritten.
_CAS_LUA = """
if redis.call('TYPE', KEYS[1]).ok == 'string' then redis.call('DEL', KEYS[1]) end
local current = tonumber(redis.call('HGET', KEYS[1], 'v'))
if current and current > tonumber(ARGV[1]) then return 0 end
redis.call('HSET', KEYS[1], 'v', ARGV[2], 'state', ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[4])
return 1
"""

# Removes a copy only if it is still the one this writer put there.
_DROP_IF_VERSION_LUA = """
if tonumber(redis.call('HGET', KEYS[1], 'v')) == tonumber(ARGV[1]) then return redis.call('DEL', KEYS[1]) end
return 0
"""


class RedisV4SessionStore:
    """Redis as the shared hot tier, Postgres ``v4_session_state`` as durable checkpoint.

    * Every write is a compare-and-set on ``store_version`` (carried inside the state), so a worker
      holding an old copy gets ``StaleSessionError`` instead of overwriting a newer turn.
    * No session is cached in this process: a read comes from Redis (checked against Postgres for a
      newer version) or, when Redis is down, from Postgres every time.
    * ``_unsaved`` holds only writes that reached neither Redis nor Postgres, so an interview
      survives with no storage at all (single process, best effort).

    The calls block; async code goes through ``app.engine.store_io``.
    """

    def __init__(self, redis_client=None, sync_engine=None, durable=None):
        # The arguments are injection points for tests; omitted, the real wiring is used.
        self._client = redis_client if redis_client is not None else create_sync_client()
        if self._client is None:
            logger.warning("SESSION_STORE_BACKEND=redis but there is no usable REDIS_URL")
        if durable is None:
            engine = sync_engine if sync_engine is not None else _create_sync_engine()
            durable = PostgresCheckpoint(engine) if engine is not None else None
        self._durable = durable
        self._breaker = Breaker("session store")
        self._unsaved: dict[str, InterviewState] = {}

    # -- Redis, never raising ---------------------------------------------

    def _redis_up(self) -> bool:
        return self._client is not None and self._breaker.allows()

    def _redis_read(self, session_id: str) -> InterviewState | None:
        if not self._redis_up():
            return None
        key = self._key(session_id)
        try:
            try:
                raw = self._client.hget(key, "state")
            except ResponseError:  # a string written by the previous, unversioned format
                raw = self._client.get(key)
            return _state_from_json(raw) if raw is not None else None
        except Exception as exc:  # noqa: BLE001
            self._breaker.failed(exc)
            return None

    def _redis_write(self, session_id: str, state: InterviewState, expected: int) -> bool | None:
        """True = written, False = refused as stale, None = Redis unreachable."""
        if not self._redis_up():
            return None
        try:
            return bool(self._client.eval(
                _CAS_LUA, 1, self._key(session_id), expected, state["store_version"],
                _state_to_json(state), SESSION_TTL_SECONDS,
            ))
        except Exception as exc:  # noqa: BLE001
            self._breaker.failed(exc)
            return None

    # -- public interface (same as MemoryV4SessionStore) ------------------

    def get(self, session_id: str) -> InterviewState | None:
        state = self._redis_read(session_id)
        if self._durable is not None:
            try:
                if state is None:
                    state = self._durable.load(session_id)
                else:
                    # Postgres wins if it moved on while Redis was unreachable.
                    state = self._durable.load_if_newer(session_id, _version_of(state)) or state
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to read session %s from the database: %s", session_id, exc)
        unsaved = self._unsaved.get(session_id)
        if unsaved is not None and (state is None or _version_of(unsaved) > _version_of(state)):
            state = _state_from_json(_state_to_json(unsaved))
        return state

    def get_or_raise(self, session_id: str) -> InterviewState:
        state = self.get(session_id)
        if not state:
            raise SessionNotFoundException(session_id)
        return state

    def set(self, session_id: str, state: InterviewState) -> int:
        """Store the state read at ``state["store_version"]``; returns the new version.

        Raises ``StaleSessionError`` when someone else wrote the session since that read.
        """
        expected = _version_of(state)
        written = {**state, "store_version": expected + 1}
        outcome = self._redis_write(session_id, written, expected)
        if outcome is False:
            raise StaleSessionError(session_id, expected)
        if outcome:
            self._unsaved.pop(session_id, None)
        else:
            self._write_without_redis(session_id, written)
        return expected + 1

    def _write_without_redis(self, session_id: str, state: InterviewState) -> None:
        version = state["store_version"]
        if self._durable is not None:
            try:
                accepted = self._durable.upsert_if_newer(session_id, state, version)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Session %s saved neither to Redis nor the database: %s", session_id, exc)
            else:
                if not accepted:
                    raise StaleSessionError(session_id, version - 1)
                self._unsaved.pop(session_id, None)
                return
        current = self._unsaved.get(session_id)
        if current is not None and _version_of(current) >= version:
            raise StaleSessionError(session_id, version - 1)
        self._unsaved[session_id] = _state_from_json(_state_to_json(state))

    def checkpoint(self, session_id: str, state: InterviewState) -> None:
        """Durable write-through to Postgres (called after ``set`` on turn completion)."""
        if self._durable is None:
            return
        version = _version_of(state)
        try:
            accepted = self._durable.upsert_if_newer(session_id, state, version)
        except Exception as exc:  # noqa: BLE001 - the turn is already in Redis
            logger.warning("Failed to checkpoint session %s to the database: %s", session_id, exc)
            return
        if accepted:
            self._unsaved.pop(session_id, None)
            return
        # Postgres is ahead of this writer: its Redis copy must not be served.
        if self._redis_up():
            try:
                self._client.eval(_DROP_IF_VERSION_LUA, 1, self._key(session_id), version)
            except Exception as exc:  # noqa: BLE001
                self._breaker.failed(exc)
        raise StaleSessionError(session_id, version - 1)

    def pop(self, session_id: str) -> InterviewState | None:
        state = self.get(session_id)
        self._unsaved.pop(session_id, None)
        if self._redis_up():
            try:
                self._client.delete(self._key(session_id))
            except Exception as exc:  # noqa: BLE001
                self._breaker.failed(exc)
        if state is not None and self._durable is not None:
            try:
                self._durable.delete(session_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to delete session %s from the database: %s", session_id, exc)
        return state

    def list_active(self) -> list[dict]:
        found: dict[str, InterviewState] = dict(self._unsaved)
        if self._redis_up():
            try:
                for key in self._client.scan_iter(f"{REDIS_KEY_PREFIX}*"):
                    sid = key.removeprefix(REDIS_KEY_PREFIX)
                    state = self._redis_read(sid)
                    if state is not None:
                        found[sid] = state
            except Exception as exc:  # noqa: BLE001
                self._breaker.failed(exc)
        return [_summary(sid, state) for sid, state in found.items()]

    def count(self) -> int:
        return len(self.list_active())

    def flush(self) -> None:
        """At shutdown: push anything that never reached storage."""
        if self._durable is None:
            return
        for sid, state in list(self._unsaved.items()):
            try:
                self._durable.upsert_if_newer(sid, state, _version_of(state))
                self._unsaved.pop(sid, None)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to flush session %s: %s", sid, exc)

    def _key(self, session_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}{session_id}"

    def close(self) -> None:
        """Close the Redis client (called at app shutdown)."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Redis close failed: %s", exc)
            self._client = None

    async def aclose(self) -> None:
        """Async close wrapper (kept for lifespans that await cleanup)."""
        self.close()


# Backward-compat alias so any external code referencing the old name still works.
V4SessionStore = MemoryV4SessionStore


_STORE: "V4SessionStore | RedisV4SessionStore | None" = None


def get_v4_session_store() -> V4SessionStore:
    global _STORE
    if _STORE is None:
        # Unset: Redis whenever there is one, because the memory store is only correct with ONE worker.
        backend = os.environ.get("SESSION_STORE_BACKEND", "").strip().lower()
        if backend == "redis" or (not backend and redis_url()):
            _STORE = RedisV4SessionStore()
        else:
            _STORE = MemoryV4SessionStore()
    return _STORE
