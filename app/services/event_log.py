"""Append-only event log for the v4 interview pipeline.

Each interview event is a small JSONB row with a per-session monotonic
``seq``. The writer is best-effort and never raises (mirrors the contract
of ``interview_v4._persist_answer_turn``) so a DB blip can never break an
in-flight interview.

Schema (created by alembic migration a7f3c2e1b9d4):

    interview_events
        id        bigserial PK
        session_id uuid FK interview_sessions.id ON DELETE CASCADE
        seq       int            -- per-session monotonic order
        event_type text
        payload    jsonb
        created_at timestamptz  -- default now()

Usage (fire-and-forget from the answer pipeline):

    from app.services.event_log import get_event_log
    await get_event_log().append(session_id, "evaluation_done", {...})
"""

import json
import logging

from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


class EventLog:
    """Best-effort append-only log. ``append`` never raises."""

    def __init__(self):
        self._factory = get_session_factory()

    async def append(self, session_id: str, event_type: str, payload: dict) -> None:
        """Append one event. Non-fatal: swallowed + logged on any failure.

        ``payload`` is serialized via ``json``; non-serializable values are
        stringified by the fallback serializer so a stray object never trips
        up the interview.
        """
        if self._factory is None:
            return
        try:
            seq = await self._next_seq(session_id)
            record = {
                "session_id": session_id,
                "seq": seq,
                "event_type": event_type,
                "payload": json.dumps(payload, default=_fallback_serialize),
            }
            async with self._factory() as session:
                await session.execute(
                    _INSERT_EVENT_SQL,
                    {
                        "session_id": record["session_id"],
                        "seq": record["seq"],
                        "event_type": record["event_type"],
                        "payload": record["payload"],
                    },
                )
                await session.commit()
        except Exception as e:  # noqa: BLE001 - best-effort by design
            logger.warning(f"event_log.append failed (swallowed): {event_type}: {e}")

    async def _next_seq(self, session_id: str) -> int:
        async with self._factory() as session:
            result = await session.execute(_MAX_SEQ_SQL, {"session_id": session_id})
            row = result.fetchone()
            base = row[0] if row and row[0] is not None else 0
        return int(base) + 1

    async def list(self, session_id: str, limit: int = 200) -> list[dict]:
        """Fetch recent events for a session (for debugging/replay)."""
        if self._factory is None:
            return []
        async with self._factory() as session:
            result = await session.execute(
                _SELECT_EVENTS_SQL,
                {"session_id": session_id, "limit": limit},
            )
            rows = result.fetchall()
        out = []
        for r in rows:
            try:
                payload = json.loads(r.payload) if isinstance(r.payload, str) else r.payload
            except Exception:
                payload = {"raw": str(r.payload)}
            out.append(
                {
                    "seq": r.seq,
                    "event_type": r.event_type,
                    "payload": payload,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return out


def _fallback_serialize(obj):
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


# --------------------------------------------------------------------------- #
# SQL (kept as constants so dialect stays explicit and reviewable)           #
# --------------------------------------------------------------------------- #

_INSERT_EVENT_SQL = (
    "INSERT INTO interview_events (session_id, seq, event_type, payload) "
    "VALUES (:session_id, :seq, :event_type, CAST(:payload AS jsonb))"
)

_MAX_SEQ_SQL = (
    "SELECT MAX(seq) FROM interview_events WHERE session_id = :session_id"
)

_SELECT_EVENTS_SQL = (
    "SELECT seq, event_type, payload, created_at "
    "FROM interview_events WHERE session_id = :session_id "
    "ORDER BY seq ASC LIMIT :limit"
)


_log: EventLog | None = None


def get_event_log() -> EventLog:
    global _log
    if _log is None:
        _log = EventLog()
    return _log
