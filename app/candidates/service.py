from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password
from app.candidates.schemas import (
    CandidateAuthResponse,
    CandidateClaimPendingResponse,
    CandidateClaimRequest,
    CandidateInterviewResponse,
    CandidateLoginRequest,
    CandidateProfileResponse,
    CandidateRegisterRequest,
    CandidateTokenResponse,
    CandidateUpdateRequest,
    PracticeStartResponse,
)
from app.config import settings
from app.database.deps import get_db
from app.models.db import (
    CandidateInvitation,
    CandidateProfile,
    CandidateRefreshToken,
    InterviewSession,
    Organization,
)
from app.services.it_role_resolver import resolve_it_role
from app.services.v4_session_store import get_v4_session_store
from app.config.interview_styles import get_style
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.data.competency_resolver import default_taxonomy, resolve_competencies, taxonomy_for_state
from app.models.db import EvidenceStore


async def _find_by_email(email: str, db: AsyncSession) -> Optional[CandidateProfile]:
    """Case-insensitive lookup so a guest profile can be claimed regardless of casing."""
    result = await db.execute(
        select(CandidateProfile).where(func.lower(CandidateProfile.email) == email.strip().lower())
    )
    return result.scalars().first()


CLAIM_TOKEN_TTL = timedelta(hours=24)


async def _start_account_claim(candidate: CandidateProfile, db: AsyncSession) -> CandidateClaimPendingResponse:
    """Email the inbox owner a link to claim an existing guest profile.

    The password is deliberately NOT accepted here: it is set on the claim page, after the
    link proves ownership of the inbox. Otherwise anyone could register a victim's email
    with their own password and later ride on the victim's "verify" click.
    """
    import secrets

    from app.services.email import send_email

    token = secrets.token_urlsafe(32)
    candidate.verification_token_hash = _hash(token)
    candidate.verification_sent_at = datetime.now(timezone.utc)
    await db.commit()

    await send_email(
        to=candidate.email,
        subject="Finish setting up your account — AI Interview Agent",
        template_name="account_claim.html",
        CANDIDATE_NAME=candidate.name,
        CLAIM_URL=f"{settings.APP_URL.rstrip('/')}/candidate/claim?token={token}",
        APP_URL=settings.APP_URL.rstrip("/"),
    )
    return CandidateClaimPendingResponse()


async def complete_claim(req: CandidateClaimRequest, db: AsyncSession) -> CandidateAuthResponse:
    """Finish claiming a guest profile: valid emailed token + chosen password."""
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.verification_token_hash == _hash(req.token))
    )
    candidate = result.scalars().first()
    expired = (
        candidate is None
        or candidate.verification_sent_at is None
        or datetime.now(timezone.utc) - candidate.verification_sent_at > CLAIM_TOKEN_TTL
    )
    if candidate is None or candidate.is_registered or expired:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link is invalid or has expired")

    candidate.password_hash = hash_password(req.password)
    if req.name and req.name.strip():
        candidate.name = req.name.strip()
    candidate.is_registered = True
    candidate.is_verified = True  # the emailed link proved inbox ownership
    candidate.verified_at = datetime.now(timezone.utc)
    candidate.verification_token_hash = None
    await db.commit()
    await db.refresh(candidate)
    return await _build_auth_response(candidate, db)


async def register(
    req: CandidateRegisterRequest, db: AsyncSession
) -> CandidateAuthResponse | CandidateClaimPendingResponse:
    existing = await _find_by_email(req.email, db)

    if existing is not None and existing.is_registered:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    if existing is not None:
        # A guest profile (earlier applications) already owns this email: claim it by email link.
        return await _start_account_claim(existing, db)

    candidate = CandidateProfile(
        id=uuid.uuid4(),
        email=req.email.strip(),
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

    candidate = await _find_by_email(email, db)

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
        if not candidate.is_registered:
            # Claim a guest profile: keep the id (and all history), mark registered.
            candidate.is_registered = True
        if google_data.get("email_verified") and not candidate.is_verified:
            # Google has proven inbox ownership. Anything set up before that proof
            # (a password or sessions from an unverified claim) is not trusted.
            candidate.password_hash = None
            await db.execute(
                update(CandidateRefreshToken)
                .where(CandidateRefreshToken.candidate_id == candidate.id)
                .values(revoked=True)
            )
            candidate.is_verified = True
            candidate.verified_at = datetime.now(timezone.utc)

    return await _build_auth_response(candidate, db)


async def refresh(refresh_token: str, db: AsyncSession) -> CandidateTokenResponse:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    token_id = payload.get("jti")
    candidate_id = payload.get("sub")
    if not token_id or not candidate_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    stored = await db.execute(
        select(CandidateRefreshToken).where(CandidateRefreshToken.token_hash == _hash(token_id))
    )
    stored_token = stored.scalar_one_or_none()
    if not stored_token or stored_token.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked or not found")

    stored_token.revoked = True

    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.id == UUID(candidate_id))
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Candidate not found")

    new_token_id = uuid.uuid4().hex
    new_refresh = CandidateRefreshToken(
        id=uuid.uuid4(),
        candidate_id=UUID(candidate_id),
        token_hash=_hash(new_token_id),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(new_refresh)

    access_token = create_access_token(candidate_id, token_type="candidate_access")
    refresh_token_str = create_refresh_token(candidate_id, new_token_id)

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
        select(InterviewSession, Organization)
        .outerjoin(Organization, InterviewSession.org_id == Organization.id)
        .where(InterviewSession.candidate_profile_id == candidate_id)
        .order_by(InterviewSession.started_at.desc())
    )
    interviews = []
    for session, organization in result.all():
        interviews.append(CandidateInterviewResponse(
            id=session.id,
            job_role=session.job_role_snapshot,
            session_type=session.session_type or "",
            interaction_mode=session.interaction_mode,
            status=session.status,
            final_score=session.final_score,
            started_at=session.started_at,
            ended_at=session.ended_at,
            department_name=organization.name if organization else None,
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

    organization_result = await db.execute(
        select(Organization).where(Organization.id == session.org_id)
    )
    organization = organization_result.scalar_one_or_none()

    return {
        "id": session.id,
        "job_role": session.job_role_snapshot,
        "session_type": session.session_type,
        "interaction_mode": session.interaction_mode,
        "status": session.status,
        "final_score": session.final_score,
        "final_feedback": session.final_feedback,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "department_name": organization.name if organization else None,
        "department_id": None,
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


async def get_competency_scores(candidate_id: UUID, db: AsyncSession) -> list[dict]:
    session_ids = (
        select(InterviewSession.id)
        .where(InterviewSession.candidate_profile_id == candidate_id)
    )
    result = await db.execute(
        select(
            EvidenceStore.competency,
            func.avg(EvidenceStore.score).label("avg_score"),
            func.count(EvidenceStore.id).label("evidence_count"),
        )
        .where(EvidenceStore.session_id.in_(session_ids))
        .group_by(EvidenceStore.competency)
    )
    rows = result.all()

    taxonomy_map = {c["id"]: c for c in COMPETENCY_TAXONOMY}
    scores = []
    for competency, avg_score, evidence_count in rows:
        info = taxonomy_map.get(competency, {})
        scores.append({
            "competency": competency,
            "name": info.get("name") or competency.replace("_", " ").title(),
            "category": info.get("category", "other"),
            "average_score": round(float(avg_score), 1),
            "evidence_count": evidence_count,
        })

    scores.sort(key=lambda x: x["average_score"])
    return scores


async def start_practice(
    candidate_id: UUID,
    job_role: str,
    difficulty: str,
    tech_stack: Optional[str],
    num_questions: int,
    interview_style: str,
    db: AsyncSession,
) -> PracticeStartResponse:
    it_role = await resolve_it_role(db, job_role)
    session = InterviewSession(
        id=uuid.uuid4(),
        org_id=None,
        it_role_id=it_role.id,
        candidate_profile_id=candidate_id,
        job_role_snapshot=job_role,
        session_type="practice",
        interaction_mode="typing",
        total_questions=num_questions,
        engine_version="v4",
    )
    db.add(session)
    await db.flush()

    # Read profile_data for v4 state seed
    candidate_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.id == candidate_id)
    )
    candidate = candidate_result.scalar_one_or_none()
    profile_data = candidate.profile_data if candidate else None

    await db.commit()

    # Seed v4 state with AURA (single conductor mode — style selection is gone)
    style = get_style("AURA")
    try:
        # The IT role's own catalog competencies; the generic IT taxonomy only if the role has none.
        practice_taxonomy = await resolve_competencies(db, it_role_id=it_role.id, use_llm=False)
    except Exception:  # noqa: BLE001 - never fail a practice start on taxonomy lookup
        practice_taxonomy = default_taxonomy()
    competency_taxonomy, required_competencies, domain_label = taxonomy_for_state(
        practice_taxonomy, priority_map=style.get("base_competency_priority")
    )
    store = get_v4_session_store()
    state = {
        "session_id": str(session.id),
        "job_role": job_role,
        "org_id": None,
        "it_role_id": str(it_role.id),
        "interview_style": style,
        "persona": style.get("persona", "friendly"),
        "difficulty_level": style.get("difficulty_range", (1, 3))[0],
        "candidate_profile": {
            "full_name": candidate.name if candidate else "Candidate",
            "headline": "",
            "strengths": list(profile_data.get("strengths", [])) if profile_data else [],
            "weaknesses": list(profile_data.get("weaknesses", [])) if profile_data else [],
        },
        "competency_taxonomy": competency_taxonomy,
        "domain_label": domain_label,
        "required_competencies": required_competencies,
        "conversation_history": [],
        "question_number": 0,
        "current_question": "",
        "candidate_answer": "",
        "flow_type": "v4_evidence_driven",
        "nodes_executed": [],
        "start_time": datetime.now(timezone.utc).isoformat(),
        "hypotheses": [],
        "hypothesis_target": None,
        "evidence_store": [],
        "competency_summary": {},
        "unified_evaluation": {},
        "evaluation_score": None,
        "observations": [],
        "competency_plan": [],
        "next_competency": None,
        "interview_strategy": {},
        "reflection_action": "probe",
        "evidence_sufficiency": {},
        "hiring_recommendation": {},
        "contradictions": [],
        "consistency_checks": [],
        "extracted_evidence": [],
        "max_questions": style.get("max_questions", 20),
        "questions_asked": [],
        "question_objective": {},
        "skip_evaluation": False,
        "evaluator_mode": style.get("evaluator_mode", "unified"),
        "strategy_cache_valid": False,
    }
    store.set(str(session.id), state)

    return PracticeStartResponse(
        session_id=session.id,
        job_role=job_role,
        total_questions=num_questions,
        interview_style=interview_style,
    )


async def _build_auth_response(candidate: CandidateProfile, db: AsyncSession) -> CandidateAuthResponse:
    access_token = create_access_token(str(candidate.id), token_type="candidate_access")

    token_id = uuid.uuid4().hex
    refresh_token_str = create_refresh_token(str(candidate.id), token_id)

    db.add(CandidateRefreshToken(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        token_hash=_hash(token_id),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    ))

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
