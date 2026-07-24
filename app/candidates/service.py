from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, decode_token
from app.auth.password import hash_password, verify_password
from app.candidates.schemas import (
    CandidateAuthResponse,
    CandidateInterviewResponse,
    CandidateLoginRequest,
    CandidateProfileResponse,
    CandidateRegisterRequest,
    CandidateTokenResponse,
    CandidateUpdateRequest,
    PracticeStartResponse,
)
from app.database.deps import get_db
from app.models.db import (
    CandidateInvitation,
    CandidateProfile,
    CandidateSession,
    Department,
    InterviewSession,
)


async def register(req: CandidateRegisterRequest, db: AsyncSession) -> CandidateAuthResponse:
    existing = await db.execute(select(CandidateProfile).where(CandidateProfile.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    candidate = CandidateProfile(
        id=uuid.uuid4(),
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        is_registered=True,
        is_verified=False,
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)

    return await _build_auth_response(candidate, db)


async def login(req: CandidateLoginRequest, db: AsyncSession) -> CandidateAuthResponse:
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.email == req.email))
    candidate = result.scalar_one_or_none()
    if not candidate or not candidate.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not verify_password(req.password, candidate.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return await _build_auth_response(candidate, db)


async def google_login(google_data: dict, db: AsyncSession) -> CandidateAuthResponse:
    email = google_data.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by Google")

    name = google_data.get("name", email.split("@")[0])

    result = await db.execute(select(CandidateProfile).where(CandidateProfile.email == email))
    candidate = result.scalar_one_or_none()

    if not candidate:
        candidate = CandidateProfile(
            id=uuid.uuid4(),
            email=email,
            name=name,
            google_id=google_data.get("sub"),
            is_registered=True,
            is_verified=google_data.get("email_verified", False),
            verified_at=datetime.now(timezone.utc) if google_data.get("email_verified") else None,
        )
        db.add(candidate)
    else:
        candidate.google_id = google_data.get("sub")

    return await _build_auth_response(candidate, db)


async def refresh(refresh_token: str, db: AsyncSession) -> CandidateTokenResponse:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "candidate_refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    candidate_id = payload.get("sub")
    if not candidate_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.id == UUID(candidate_id))
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Candidate not found")

    access_token = create_access_token(candidate_id, token_type="candidate_access")
    refresh_token_str = create_access_token(candidate_id, token_type="candidate_refresh")

    return CandidateTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
    )


async def get_profile(candidate_id: UUID, db: AsyncSession) -> CandidateProfileResponse:
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return CandidateProfileResponse.model_validate(candidate)


async def update_profile(candidate_id: UUID, req: CandidateUpdateRequest, db: AsyncSession) -> CandidateProfileResponse:
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)

    await db.commit()
    await db.refresh(candidate)
    return CandidateProfileResponse.model_validate(candidate)


async def get_interviews(candidate_id: UUID, db: AsyncSession) -> list[CandidateInterviewResponse]:
    result = await db.execute(
        select(InterviewSession, Department)
        .outerjoin(Department, InterviewSession.department_id == Department.id)
        .where(InterviewSession.candidate_profile_id == candidate_id)
        .order_by(InterviewSession.started_at.desc())
    )
    interviews = []
    for session, department in result.all():
        interviews.append(CandidateInterviewResponse(
            id=session.id,
            job_role=session.job_role,
            session_type=session.session_type or "",
            interaction_mode=session.interaction_mode,
            status=session.status,
            final_score=session.final_score,
            started_at=session.started_at,
            ended_at=session.ended_at,
            department_name=department.name if department else None,
        ))
    return interviews


async def get_interview_detail(candidate_id: UUID, interview_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == interview_id,
            InterviewSession.candidate_profile_id == candidate_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    department_result = await db.execute(select(Department).where(Department.id == session.department_id))
    department = department_result.scalar_one_or_none()

    return {
        "id": session.id,
        "job_role": session.job_role,
        "session_type": session.session_type,
        "interaction_mode": session.interaction_mode,
        "status": session.status,
        "final_score": session.final_score,
        "final_feedback": session.final_feedback,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "department_name": department.name if department else None,
        "department_id": department.id if department else None,
    }


async def get_stats(candidate_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.candidate_profile_id == candidate_id,
        )
    )
    sessions = result.scalars().all()
    total = len(sessions)
    scored = [s for s in sessions if s.final_score is not None]
    avg_score = sum(float(s.final_score) for s in scored) / len(scored) if scored else None
    completed = len([s for s in sessions if s.status == "completed"])
    active = len([s for s in sessions if s.status == "active"])

    return {
        "total_interviews": total,
        "completed_interviews": completed,
        "active_interviews": active,
        "average_score": float(avg_score) if avg_score else None,
    }


async def start_practice(
    candidate_id: UUID,
    job_role: str,
    difficulty: str,
    tech_stack: Optional[str],
    num_questions: int,
    db: AsyncSession,
) -> PracticeStartResponse:
    session = InterviewSession(
        id=uuid.uuid4(),
        candidate_profile_id=candidate_id,
        job_role=job_role,
        session_type="mock",
        interaction_mode="typing",
        total_questions=num_questions,
    )
    db.add(session)
    await db.flush()

    cs = CandidateSession(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        session_id=session.id,
    )
    db.add(cs)
    await db.commit()

    return PracticeStartResponse(
        session_id=session.id,
        job_role=job_role,
        total_questions=num_questions,
    )


async def _build_auth_response(candidate: CandidateProfile, db: AsyncSession) -> CandidateAuthResponse:
    access_token = create_access_token(str(candidate.id), token_type="candidate_access")
    refresh_token_str = create_access_token(str(candidate.id), token_type="candidate_refresh")

    await db.flush()
    await db.refresh(candidate)

    return CandidateAuthResponse(
        candidate=CandidateProfileResponse.model_validate(candidate),
        tokens=CandidateTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        ),
    )


def _hash(token_id: str) -> str:
    return hashlib.sha256(token_id.encode()).hexdigest()
