"""Rules shared by every kind of account.

Hiring-side users and candidates are all rows of ``users``. A candidate also has a ``candidate_profiles`` row with the same id;
a hiring account owns an organization or is an admin. Which kind of session a login may create is decided here, never by the
caller's choice of endpoint alone, and a refresh token remembers the kind it was issued for (``RefreshToken.actor``).
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password
from app.models.db import CandidateProfile, Organization, RefreshToken, User, UserPasswordResetToken

ACTOR_ORG = "org"
ACTOR_CANDIDATE = "candidate"

REFRESH_TTL = timedelta(days=7)
# Expired refresh tokens are kept this long after they expire (support/debugging), then deleted.
REFRESH_PURGE_GRACE = timedelta(days=7)
RESET_TTL = timedelta(hours=1)

_dummy_hash: Optional[str] = None


def hash_token(token_id: str) -> str:
    return hashlib.sha256(token_id.encode()).hexdigest()


def clean_email(email: str) -> str:
    return (email or "").strip()


async def find_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Case-insensitive: "A@x.com" and "a@x.com" are one person."""
    result = await db.execute(select(User).where(func.lower(User.email) == clean_email(email).lower()))
    return result.scalars().first()


async def is_org_account(db: AsyncSession, user: User) -> bool:
    """A hiring-side account: an admin, or the owner of an organization."""
    if user.is_admin:
        return True
    result = await db.execute(select(Organization.id).where(Organization.owner_user_id == user.id).limit(1))
    return result.first() is not None


async def get_candidate_profile(db: AsyncSession, user_id: UUID) -> Optional[CandidateProfile]:
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == user_id))
    return result.scalar_one_or_none()


def password_matches(user: Optional[User], password: str) -> bool:
    """Constant-effort check: a missing account or one without a password still costs a bcrypt comparison, so response time
    does not reveal whether an email is registered."""
    global _dummy_hash
    stored = user.password_hash if user is not None else None
    if not stored:
        if _dummy_hash is None:
            _dummy_hash = hash_password(uuid.uuid4().hex)
        verify_password(password, _dummy_hash)
        return False
    return verify_password(password, stored)


# ---------------------------------------------------------------------------------------------------- sessions
def issue_refresh_token(db: AsyncSession, user_id: UUID, actor: str) -> str:
    """Stores a new refresh token bound to the kind of session it may mint and returns the signed token."""
    if actor not in (ACTOR_ORG, ACTOR_CANDIDATE):
        raise ValueError(f"unknown actor {actor!r}")
    token_id = uuid.uuid4().hex
    db.add(RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=hash_token(token_id),
        expires_at=datetime.now(timezone.utc) + REFRESH_TTL,
        revoked=False,
        actor=actor,
    ))
    return create_refresh_token(str(user_id), token_id)


async def rotate_refresh_token(
    db: AsyncSession,
    refresh_token: str,
    actor: str,
    allow: Optional[Callable[[AsyncSession, User], Awaitable[bool]]] = None,
) -> tuple[User, str]:
    """Exchange a refresh token for a new one. The stored token must be unrevoked, unexpired, issued for THIS kind of session
    and for the user named inside the signed token, and ``allow`` (if given) must accept the account; all of it is checked
    before anything is changed. Returns the user and the new signed refresh token."""
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    token_id, subject = payload.get("jti"), payload.get("sub")
    if not token_id or not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    try:
        user_id = UUID(str(subject))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token_id)))
    stored = result.scalar_one_or_none()
    if (
        stored is None
        or stored.revoked
        or stored.actor != actor
        or stored.user_id != user_id
        or stored.expires_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked or not found")

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active or (allow is not None and not await allow(db, user)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not available")

    stored.revoked = True
    return user, issue_refresh_token(db, user.id, actor)


async def revoke_all_sessions(db: AsyncSession, user_id: UUID, actor: Optional[str] = None) -> None:
    """Revoke every live refresh token of an account (optionally only one kind of session)."""
    stmt = update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)  # noqa: E712
    if actor is not None:
        stmt = stmt.where(RefreshToken.actor == actor)
    await db.execute(stmt.values(revoked=True))


async def purge_expired_refresh_tokens(db: AsyncSession, grace: timedelta = REFRESH_PURGE_GRACE) -> int:
    """Delete refresh tokens that expired more than ``grace`` ago. Rotation only marks old tokens revoked, so without this
    the table grows by a row on every login and refresh. Live tokens are never touched. Returns the number of rows deleted."""
    cutoff = datetime.now(timezone.utc) - grace
    result = await db.execute(delete(RefreshToken).where(RefreshToken.expires_at < cutoff))
    await db.commit()
    return int(result.rowcount or 0)


# ---------------------------------------------------------------------------------------------- password reset
async def start_password_reset(db: AsyncSession, user: User) -> str:
    """Create a one-hour reset token (earlier unused ones stop working) and return the raw token for the email."""
    await db.execute(
        update(UserPasswordResetToken)
        .where(UserPasswordResetToken.user_id == user.id, UserPasswordResetToken.used == False)  # noqa: E712
        .values(used=True)
    )
    token = secrets.token_urlsafe(32)
    db.add(UserPasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + RESET_TTL,
    ))
    await db.commit()
    return token


async def finish_password_reset(db: AsyncSession, token: str, new_password: str) -> User:
    """Set a new password from an emailed token, and sign the account out everywhere (every kind of session)."""
    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    result = await db.execute(
        select(UserPasswordResetToken).where(
            UserPasswordResetToken.token_hash == hash_token(token),
            UserPasswordResetToken.used == False,  # noqa: E712
            UserPasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
    )
    reset = result.scalar_one_or_none()
    if reset is None:
        raise invalid
    user_result = await db.execute(select(User).where(User.id == reset.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise invalid  # same answer as a bad token: do not reveal which accounts exist

    user.password_hash = hash_password(new_password)
    reset.used = True
    await revoke_all_sessions(db, user.id)
    await db.commit()
    return user
