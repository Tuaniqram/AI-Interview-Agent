import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Set
from uuid import uuid4

from app.graph.interview_state import InterviewState
from app.exceptions import SessionNotFoundException

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "v4_sessions.json")


class V4SessionStore:
    """Persistent store for v4 interview sessions.

    Fast in-memory dict for read/write.
    Persists to PostgreSQL (v4_session_state table) or JSON file fallback.
    Survives server restarts — sessions are loaded from DB on init.
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

    def _save_to_db(self) -> None:
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO v4_session_state (session_id, state, updated_at)
            VALUES (:sid, :state::jsonb, now())
            ON CONFLICT (session_id)
            DO UPDATE SET state = EXCLUDED.state, updated_at = now()
        """)
        with self._sync_engine.begin() as conn:
            for sid in list(self._dirty):
                state = self._sessions.get(sid)
                if state:
                    conn.execute(stmt, {
                        "sid": sid,
                        "state": json.dumps(state, default=_json_serialize),
                    })

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
                        text("DELETE FROM v4_session_state WHERE updated_at < now() - make_interval(hours => :hours)"),
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


def _json_serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


_store: V4SessionStore | None = None


def get_v4_session_store() -> V4SessionStore:
    global _store
    if _store is None:
        _store = V4SessionStore()
    return _store
