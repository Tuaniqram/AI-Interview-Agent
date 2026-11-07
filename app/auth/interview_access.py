"""Signed per-session access tokens for the interview WebSocket.

Guests have no account, so "who may drive this interview?" cannot be answered with a
candidate login. The application invitation (or a public listing start) instead yields
a token bound to exactly one session id. The WebSocket accepts either the owning
candidate's login token or this one: nothing else.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.auth.jwt import ALGORITHM, decode_token
from app.config import settings

TOKEN_TYPE = "interview_access"
INTERVIEW_ACCESS_TTL = timedelta(hours=12)


def create_interview_access_token(session_id) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(session_id),
            "type": TOKEN_TYPE,
            "iat": now,
            "exp": now + INTERVIEW_ACCESS_TTL,
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_interview_access_token(token: Optional[str]) -> Optional[str]:
    """Session id the token grants access to, or ``None`` if invalid/expired/wrong type."""
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("type") != TOKEN_TYPE:
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None
