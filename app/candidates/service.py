from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.accounts import (
    ACTOR_CANDIDATE,
    clean_email,
    find_user_by_email,
    get_candidate_profile,
    hash_token,
    issue_refresh_token,
    password_matches,
    revoke_all_sessions,
    rotate_refresh_token,
)
from app.auth.jwt import create_access_token
from app.auth.password import hash_password
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
from app.services.feedback_text import legacy_to_plain
from app.database.deps import get_db
from app.models.db import (
    CandidateInvitation,
    CandidateProfile,
    InterviewSession,
    Organization,
    User,
)
from app.services.it_role_resolver import resolve_it_role
from app.services.v4_session_store import get_v4_session_store
from app.config.interview_styles import get_style
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.data.competency_resolver import default_taxonomy, resolve_competencies, taxonomy_for_state
from app.models.db import EvidenceStore


async def _find_by_email(email: str, db: AsyncSession) -> Optional[User]:
    """Case-insensitive lookup so a guest account can be claimed regardless of casing."""
    return await find_user_by_email(db, email)


CLAIM_TOKEN_TTL = timedelta(hours=24)

_BAD_CREDENTIALS = "Invalid email or password"


async def _ensure_profile(user: User, db: AsyncSession) -> CandidateProfile:
    """The candidate-only data of an account; created on first use (same id as the user)."""
    profile = await get_candidate_profile(db, user.id)
    if profile is None:
        profile = CandidateProfile(id=user.id, user=user)
        db.add(profile)
        await db.flush()
    return profile


async def _is_candidate_account(db: AsyncSession, user: User) -> bool:
    return bool(user.is_registered) and await get_candidate_profile(db, user.id) is not None


async def _start_account_claim(user: User, db: AsyncSession) -> CandidateClaimPendingResponse:
    """Email the inbox owner a link to claim an existing guest account.

    The password is deliberately NOT accepted here: it is set on the claim page, after the
    link proves ownership of the inbox. Otherwise anyone could register a victim's email
    with their own password and later ride on the victim's "verify" click.
    """
    import secrets

    from app.services.email import send_email

    token = secrets.token_urlsafe(32)
    user.verification_token_hash = _hash(token)
    user.verification_sent_at = datetime.now(timezone.utc)
    await db.commit()

    await send_email(
        to=user.email,
        subject="Finish setting up your account — AI Interview Agent",
        template_name="account_claim.html",
        CANDIDATE_NAME=user.name,
        CLAIM_URL=f"{settings.APP_URL.rstrip('/')}/candidate/claim?token={token}",
        APP_URL=settings.APP_URL.rstrip("/"),
    )
    return CandidateClaimPendingResponse()


async def complete_claim(req: CandidateClaimRequest, db: AsyncSession) -> CandidateAuthResponse:
    """Finish claiming a guest account: valid emailed token + chosen password."""
    result = await db.execute(select(User).where(User.verification_token_hash == _hash(req.token)))
    user = result.scalars().first()
    expired = (
        user is None
        or user.verification_sent_at is None
        or datetime.now(timezone.utc) - user.verification_sent_at > CLAIM_TOKEN_TTL
    )
    if user is None or user.is_registered or expired:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link is invalid or has expired")

    user.password_hash = hash_password(req.password)
    if req.name and req.name.strip():
        user.name = req.name.strip()
    user.is_registered = True
    user.is_verified = True  # the emailed link proved inbox ownership
    user.verified_at = datetime.now(timezone.utc)
    user.verification_token_hash = None
    candidate = await _ensure_profile(user, db)
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
        # A guest account (earlier applications) already owns this email: claim it by email link.
        return await _start_account_claim(existing, db)

    user = User(
        id=uuid.uuid4(),
        email=clean_email(req.email),
        password_hash=hash_password(req.password),
        name=req.name,
        is_registered=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    candidate = CandidateProfile(id=user.id, user=user)
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)

    return await _build_auth_response(candidate, db)


async def login(req: CandidateLoginRequest, db: AsyncSession) -> CandidateAuthResponse:
    user = await _find_by_email(req.email, db)
    # Same answer for every failure (no such account, no password, wrong password, deactivated, not a candidate account).
    if not password_matches(user, req.password) or not user.is_active or not user.is_registered:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_BAD_CREDENTIALS)
    candidate = await get_candidate_profile(db, user.id)
    if candidate is None:  # a hiring-only account cannot use the candidate sign-in
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_BAD_CREDENTIALS)

    return await _build_auth_response(candidate, db)


async def google_login(google_data: dict, db: AsyncSession) -> CandidateAuthResponse:
    from app.auth.accounts import is_org_account

    email = google_data.get("email")
    subject = google_data.get("sub")
    if not email or not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by Google")
    # verify_google_token already rejects unverified emails; this keeps the rule even if the service is called directly.
    if google_data.get("email_verified") is not True:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your Google email address is not verified")

    name = google_data.get("name") or email.split("@")[0]
    now = datetime.now(timezone.utc)

    user = await _find_by_email(email, db)

    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=clean_email(email),
            password_hash=None,
            name=name,
            google_id=subject,
            is_registered=True,
            is_verified=True,
            verified_at=now,
        )
        db.add(user)
        await db.flush()
    else:
        if not user.is_active or (user.google_id and user.google_id != subject):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This Google account cannot sign in here")
        if not user.google_id:
            user.google_id = subject
        if not user.is_registered:
            # Claim a guest account: keep the id (and all history), mark registered.
            user.is_registered = True
        if not user.is_verified:
            # Google has proven inbox ownership. For a candidate-only account, anything set up before that proof (a password,
            # or sessions from an unverified claim) is not trusted. A hiring account keeps its password and its hiring sessions.
            if not await is_org_account(db, user):
                user.password_hash = None
                await revoke_all_sessions(db, user.id, ACTOR_CANDIDATE)
            user.is_verified = True
            user.verified_at = now

    candidate = await _ensure_profile(user, db)
    return await _build_auth_response(candidate, db)


async def refresh(refresh_token: str, db: AsyncSession) -> CandidateTokenResponse:
    user, refresh_token_str = await rotate_refresh_token(
        db, refresh_token, ACTOR_CANDIDATE, allow=_is_candidate_account
    )
    return CandidateTokenResponse(
        access_token=create_access_token(str(user.id), token_type="candidate_access"),
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
            org_name=organization.name if organization else None,
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
        "final_feedback": legacy_to_plain(session.final_feedback),
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "org_name": organization.name if organization else None,
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
        engine_version="v5",
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
        "flow_type": "v5_evidence_driven",
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
    refresh_token_str = issue_refresh_token(db, candidate.id, ACTOR_CANDIDATE)

    await db.flush()
    await db.refresh(candidate)

    return CandidateAuthResponse(
        candidate=CandidateProfileResponse.model_validate(candidate),
        tokens=CandidateTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        ),
    )


_hash = hash_token
