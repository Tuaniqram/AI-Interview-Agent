"""Input and concurrency guards for the interview WebSocket (pure, unit-testable).

The WebSocket is the engine's trust boundary: every frame is untrusted. These helpers
keep one malformed, oversized, repeated or concurrent message from crashing a session,
burning LLM budget, or corrupting state.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from typing import Any, Optional

MAX_FRAME_BYTES = 64 * 1024        # a whole WebSocket frame
MAX_ANSWER_CHARS = 10_000          # one candidate answer
MAX_SESSION_ID_CHARS = 64
RATE_LIMIT_MESSAGES = 30           # per connection...
RATE_LIMIT_WINDOW_S = 10.0         # ...per window
IDLE_TIMEOUT_S = 15 * 60           # no frame for this long -> close

KNOWN_MESSAGE_TYPES = {"ping", "start_interview", "request_question", "submit_answer", "get_status"}


def parse_frame(raw: Any) -> tuple[Optional[dict], Optional[str]]:
    """Decode one client frame. Returns ``(message, None)`` or ``(None, error)``.

    Never raises: a bad frame must produce an error reply, not close the socket.
    """
    if not isinstance(raw, str):
        return None, "Messages must be text"
    if len(raw.encode("utf-8", errors="ignore")) > MAX_FRAME_BYTES:
        return None, f"Message too large (max {MAX_FRAME_BYTES // 1024} KB)"
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError):
        return None, "Message is not valid JSON"
    if not isinstance(data, dict):
        return None, "Message must be a JSON object"
    msg_type = data.get("type")
    if not isinstance(msg_type, str) or not msg_type:
        return None, "Message type is required"
    return data, None


def clean_message_id(value: Any) -> Any:
    """Only echo back ids that are short strings/numbers (never arbitrary structures)."""
    if isinstance(value, (str, int)) and not isinstance(value, bool) and len(str(value)) <= 64:
        return value
    return None


def validate_answer(value: Any) -> tuple[Optional[str], Optional[str]]:
    """``(answer, None)`` or ``(None, error)``. The text itself is sanitized later by the engine."""
    if not isinstance(value, str):
        return None, "Answer must be text"
    answer = value.strip()
    if not answer:
        return None, "Answer cannot be empty"
    if len(answer) > MAX_ANSWER_CHARS:
        return None, f"Answer is too long (max {MAX_ANSWER_CHARS:,} characters)"
    return answer, None


def validate_session_id(value: Any) -> Optional[str]:
    if isinstance(value, str) and 0 < len(value) <= MAX_SESSION_ID_CHARS:
        return value
    return None


class MessageRateLimiter:
    """Sliding-window limiter for one connection."""

    def __init__(self, max_messages: int = RATE_LIMIT_MESSAGES, window_s: float = RATE_LIMIT_WINDOW_S):
        self.max_messages = max_messages
        self.window_s = window_s
        self._stamps: deque[float] = deque()

    def allow(self, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        while self._stamps and now - self._stamps[0] > self.window_s:
            self._stamps.popleft()
        if len(self._stamps) >= self.max_messages:
            return False
        self._stamps.append(now)
        return True


class SessionLocks:
    """One asyncio lock per session id, so two tabs/double-clicks can't run the same
    interview step concurrently (which would double-score an answer or fork the state)."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._users: dict[str, int] = {}

    def lock(self, session_id: str) -> "_LockCtx":
        return _LockCtx(self, session_id)

    def _acquire_ref(self, session_id: str) -> asyncio.Lock:
        self._users[session_id] = self._users.get(session_id, 0) + 1
        return self._locks.setdefault(session_id, asyncio.Lock())

    def _release_ref(self, session_id: str) -> None:
        left = self._users.get(session_id, 1) - 1
        if left <= 0:  # drop idle locks so the dict can't grow forever
            self._users.pop(session_id, None)
            self._locks.pop(session_id, None)
        else:
            self._users[session_id] = left

    def __len__(self) -> int:
        return len(self._locks)


class _LockCtx:
    def __init__(self, owner: SessionLocks, session_id: str) -> None:
        self._owner, self._sid = owner, session_id
        self._lock: Optional[asyncio.Lock] = None

    async def __aenter__(self):
        self._lock = self._owner._acquire_ref(self._sid)
        await self._lock.acquire()

    async def __aexit__(self, *exc):
        assert self._lock is not None
        self._lock.release()
        self._owner._release_ref(self._sid)
