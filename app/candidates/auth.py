from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.database.deps import get_db
from app.models.db import CandidateProfile

candidate_security = HTTPBearer(auto_error=False)


async def authenticate_candidate(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(candidate_security),
    db: AsyncSession = Depends(get_db),
) -> CandidateProfile:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "candidate_access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        candidate_id = payload.get("sub")
        if not candidate_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == UUID(candidate_id)))
        candidate = result.scalar_one_or_none()
        if not candidate:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Candidate not found")
        return candidate
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


async def require_verified_candidate(
    candidate: CandidateProfile = Depends(authenticate_candidate),
) -> CandidateProfile:
    if not candidate.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email address.",
        )
    return candidate


async def optional_candidate_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(candidate_security),
    db: AsyncSession = Depends(get_db),
) -> Optional[CandidateProfile]:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "candidate_access":
            return None
        candidate_id = payload.get("sub")
        if not candidate_id:
            return None
        result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == UUID(candidate_id)))
        return result.scalar_one_or_none()
    except ValueError:
        return None
