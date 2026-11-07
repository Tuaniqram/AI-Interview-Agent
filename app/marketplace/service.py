from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.deps import get_db
from app.marketplace.schemas import (
    ApplicationInvitationResponse,
    ApplicationOutcomeRequest,
    ApplicationResponse,
    ApplyRequest,
    CandidateResponseRequest,
    CreatePublicInterviewRequest,
    FitScoreRequest,
    OrgListingResponse,
    OrgPublicInterviewResponse,
    PublicInterviewResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    UpdatePublicInterviewRequest,
)
from app.auth.interview_access import create_interview_access_token
from app.candidates.resume_service import RESUMES_DIR, latest_resume_document, store_candidate_resume
from app.models.db import (
    CandidateDocument,
    CandidateProfile,
    InterviewSession,
    InterviewTemplate,
    Organization,
    PublicInterview,
    PublicInterviewSubmission,
)
from app.services.audit_log import AuditLogService
from app.services.marketplace_generator import generate_rich_description
from app.services.v4_session_store import get_v4_session_store
from app.config.interview_styles import get_style

logger = logging.getLogger(__name__)

from app.data.competency_resolver import (
    resolve_competencies,
    taxonomy_for_state,
)
from app.intelligence.role_competency_profiler import build_role_context


async def list_organizations(
    search: Optional[str] = None,
    modes: Optional[str] = None,
    expiry: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> list[OrgListingResponse]:
    now = datetime.now(timezone.utc)
    query = select(
        Organization.id,
        Organization.name,
        Organization.slug,
        Organization.description,
        Organization.website,
        Organization.logo_url,
        func.count(PublicInterview.id).label("interview_count"),
    ).outerjoin(
        PublicInterview,
        PublicInterview.org_id == Organization.id,
    ).where(
        Organization.is_active == True,
        PublicInterview.is_open == True,
        (PublicInterview.starts_at == None) | (PublicInterview.starts_at <= now),
        (PublicInterview.expires_at == None) | (PublicInterview.expires_at > now),
    )

    if search:
        query = query.where(Organization.name.ilike(f"%{search}%"))

    if modes:
        mode_list = [m.strip() for m in modes.split(",") if m.strip()]
        if mode_list:
            query = query.where(PublicInterview.interview_mode.in_(mode_list))

    if expiry == "7d":
        cutoff = now + timedelta(days=7)
        query = query.where(
            PublicInterview.expires_at != None,
            PublicInterview.expires_at <= cutoff,
        )
    elif expiry == "30d":
        cutoff = now + timedelta(days=30)
        query = query.where(
            PublicInterview.expires_at != None,
            PublicInterview.expires_at <= cutoff,
        )

    query = query.group_by(Organization.id)

    result = await db.execute(query)
    rows = result.all()

    return [
        OrgListingResponse(
            id=row.id,
            name=row.name,
            slug=row.slug,
            description=row.description,
            website=row.website,
            logo_url=row.logo_url,
            interview_count=row.interview_count or 0,
        )
        for row in rows
    ]


async def get_org_profile(org_slug: str, db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    org_result = await db.execute(
        select(Organization).where(Organization.slug == org_slug, Organization.is_active == True)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    interviews_result = await db.execute(
        select(
            PublicInterview,
            Organization.name.label("dept_name"),
        ).outerjoin(
            Organization, PublicInterview.org_id == Organization.id
        ).where(
            PublicInterview.org_id == org.id,
            PublicInterview.is_open == True,
            (PublicInterview.starts_at == None) | (PublicInterview.starts_at <= now),
            (PublicInterview.expires_at == None) | (PublicInterview.expires_at > now),
        )
    )
    interviews = []
    for pi, dept_name in interviews_result.all():
        interviews.append(
            PublicInterviewResponse(
                id=pi.id,
                org_id=pi.org_id,
                title=pi.title,
                description=pi.description,
                rich_description=pi.rich_description,
                interview_mode=pi.interview_mode,
                org_name=org.name,
                department_name=dept_name or "",
                skills_required=pi.skills_required,
                style_name=pi.style_name or "STANDARD",
                starts_at=pi.starts_at,
                expires_at=pi.expires_at,
            )
        )

    return {
        "org": OrgListingResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            website=org.website,
            logo_url=org.logo_url,
            interview_count=len(interviews),
        ),
        "interviews": interviews,
    }


async def get_public_interview(interview_id: str, db: AsyncSession) -> PublicInterviewResponse:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PublicInterview).where(
            PublicInterview.id == interview_id,
            PublicInterview.is_open == True,
            (PublicInterview.starts_at == None) | (PublicInterview.starts_at <= now),
            (PublicInterview.expires_at == None) | (PublicInterview.expires_at > now),
        )
    )
    pi = result.scalar_one_or_none()
    if not pi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    org_result = await db.execute(select(Organization).where(Organization.id == pi.org_id))
    org = org_result.scalar_one_or_none()

    dept_name = ""
    if pi.org_id:
        dept_result = await db.execute(
            select(Organization).where(Organization.id == pi.org_id)
        )
        dept = dept_result.scalar_one_or_none()
        dept_name = dept.name if dept else ""

    return PublicInterviewResponse(
        id=pi.id,
        org_id=pi.org_id,
        title=pi.title,
        description=pi.description,
        rich_description=pi.rich_description,
        interview_mode=pi.interview_mode,
        org_name=org.name if org else None,
        department_name=dept_name,
        skills_required=pi.skills_required,
        style_name=pi.style_name or "STANDARD",
        starts_at=pi.starts_at,
        expires_at=pi.expires_at,
    )


async def start_public_interview(
    interview_id: str,
    req: StartInterviewRequest,
    db: AsyncSession,
) -> StartInterviewResponse:
    pi_result = await db.execute(
        select(PublicInterview).where(PublicInterview.id == interview_id, PublicInterview.is_open == True)
    )
    pi = pi_result.scalar_one_or_none()
    if not pi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    # Resolve scorecard_template_id from the linked InterviewTemplate if set
    sc_template_id = None
    if pi.template_id:
        tmpl_result = await db.execute(
            select(InterviewTemplate).where(InterviewTemplate.id == pi.template_id)
        )
        tmpl = tmpl_result.scalar_one_or_none()
        if tmpl:
            sc_template_id = tmpl.scorecard_template_id

    session = InterviewSession(
        id=uuid.uuid4(),
        org_id=pi.org_id,
        it_role_id=pi.it_role_id,
        candidate_profile_id=None,
        job_role_snapshot=pi.title,
        session_type="public",
        interaction_mode=pi.interview_mode,
        engine_version="v4",
        scorecard_template_id=sc_template_id,
    )

    # G4: link to existing candidate profile if email matches
    candidate_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.email == req.candidate_email).limit(1)
    )
    candidate = candidate_result.scalar_one_or_none()
    profile_data = None
    if candidate:
        session.candidate_profile_id = candidate.id
        profile_data = candidate.profile_data

    db.add(session)
    await db.flush()

    # Seed v4 state with AURA (single conductor mode — style selection is gone)
    style = get_style("AURA")

    # Role-first resolution (F1): the listing's role facts drive competency
    # selection; the company brain is grounded separately at blueprint time.
    role_context = None
    try:
        org_name = ""
        org_result = await db.execute(
            select(Organization).where(Organization.id == pi.org_id)
        )
        org_row = org_result.scalar_one_or_none()
        if org_row:
            org_name = org_row.name or ""
        role_context = build_role_context(
            job_role=pi.title or "",
            skills_required=list(pi.skills_required) if getattr(pi, "skills_required", None) else None,
            description=pi.description or "",
            department_id=None,
            department_name="",
            org_name=org_name,
        )
    except Exception as exc:  # noqa: BLE001 - role context is best-effort
        logger.warning("Failed to build role context: %s", exc)

    taxonomy = await resolve_competencies(
        db,
        scorecard_template_id=str(sc_template_id) if sc_template_id else None,
        org_id=pi.org_id,
        role_context=role_context,
        it_role_id=pi.it_role_id,
    )
    competency_taxonomy, required_competencies, domain_label = taxonomy_for_state(
        taxonomy, priority_map=style.get("base_competency_priority")
    )
    store = get_v4_session_store()
    state = {
        "session_id": str(session.id),
        "job_role": pi.title or "Software Engineer",
        "org_id": str(pi.org_id),
        "it_role_id": str(pi.it_role_id),
        "interview_style": style,
        "persona": style.get("persona", "friendly"),
        "difficulty_level": style.get("difficulty_range", (1, 3))[0],
        "candidate_profile": {
            "full_name": req.candidate_name or "Candidate",
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

    # A real credential for this one session (the WebSocket requires it); it used to be a random
    # string that nothing ever checked.
    token = create_interview_access_token(session.id)
    submission = PublicInterviewSubmission(
        id=uuid.uuid4(),
        public_id=pi.id,
        session_id=session.id,
        candidate_email=req.candidate_email,
        candidate_name=req.candidate_name,
        started_at=datetime.now(timezone.utc),
    )
    db.add(submission)
    await db.commit()

    return StartInterviewResponse(session_id=session.id, token=token)


async def create_public_interview(
    org_id: str,
    req: CreatePublicInterviewRequest,
    db: AsyncSession,
    actor_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> OrgPublicInterviewResponse:
    now = datetime.now(timezone.utc)
    pi = PublicInterview(
        id=uuid.uuid4(),
        org_id=org_id,
        it_role_id=req.it_role_id,
        level_code=req.level_code,
        title=req.title,
        description=req.description,
        interview_mode=req.interview_mode,
        max_candidates=req.max_candidates,
        skills_required=req.skills_required,
        style_name="AURA",
        template_id=req.template_id,
        starts_at=req.starts_at,
        expires_at=req.expires_at,
        token=uuid.uuid4().hex,
        is_open=True,
    )
    db.add(pi)
    await db.commit()
    await db.refresh(pi)

    # Trigger background AI description generation
    asyncio.create_task(generate_rich_description(str(pi.id)))

    audit = AuditLogService(db)
    await audit.log(
        action="marketplace.create",
        resource_type="public_interview",
        resource_id=str(pi.id),
        user_id=actor_id,
        org_id=org_id,
        details={"title": req.title, "it_role_id": str(req.it_role_id), "interview_mode": req.interview_mode},
        ip_address=ip_address,
    )

    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    resp = OrgPublicInterviewResponse.model_validate(pi)
    resp.department_name = org.name if org else ""
    return resp


async def list_org_public_interviews(
    org_id: str,
    db: AsyncSession,
) -> list[OrgPublicInterviewResponse]:
    result = await db.execute(
        select(
            PublicInterview,
            Organization.name.label("dept_name"),
        ).outerjoin(
            Organization, PublicInterview.org_id == Organization.id
        ).where(
            PublicInterview.org_id == org_id
        ).order_by(PublicInterview.created_at.desc())
    )
    items = []
    for pi, dept_name in result.all():
        resp = OrgPublicInterviewResponse.model_validate(pi)
        resp.department_name = dept_name or ""
        items.append(resp)
    return items


async def update_public_interview(
    interview_id: str,
    req: UpdatePublicInterviewRequest,
    db: AsyncSession,
) -> OrgPublicInterviewResponse:
    result = await db.execute(
        select(PublicInterview).where(PublicInterview.id == interview_id)
    )
    pi = result.scalar_one_or_none()
    if not pi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    update_data = req.model_dump(exclude_unset=True)
    title_changed = "title" in update_data or "skills_required" in update_data
    for key, value in update_data.items():
        setattr(pi, key, value)
    pi.style_name = "AURA"  # single conductor mode — never allow a style change
    await db.commit()
    await db.refresh(pi)

    # Regenerate description if title or skills changed
    if title_changed:
        asyncio.create_task(generate_rich_description(str(pi.id)))

    dept_name = ""
    if pi.org_id:
        dept_result = await db.execute(
            select(Organization).where(Organization.id == pi.org_id)
        )
        dept = dept_result.scalar_one_or_none()
        dept_name = dept.name if dept else ""

    resp = OrgPublicInterviewResponse.model_validate(pi)
    resp.department_name = dept_name
    return resp


async def delete_public_interview(
    interview_id: str,
    db: AsyncSession,
) -> None:
    result = await db.execute(
        select(PublicInterview).where(PublicInterview.id == interview_id)
    )
    pi = result.scalar_one_or_none()
    if not pi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    await db.delete(pi)
    await db.commit()


def _application_response(
    row: PublicInterviewSubmission,
    public_title: Optional[str] = None,
    org_name: Optional[str] = None,
    resume_filename: Optional[str] = None,
) -> ApplicationResponse:
    return ApplicationResponse(
        id=row.id,
        public_id=row.public_id,
        public_title=public_title,
        org_name=org_name,
        session_id=row.session_id,
        candidate_profile_id=row.candidate_profile_id,
        resume_document_id=row.resume_document_id,
        candidate_email=row.candidate_email,
        candidate_name=row.candidate_name,
        status=row.status,
        fit_score=float(row.fit_score) if row.fit_score is not None else None,
        fit_summary=row.fit_summary,
        fit_status=row.fit_status or "pending",
        fit_breakdown=row.fit_breakdown,
        fit_evaluated_at=row.fit_evaluated_at,
        has_resume=row.resume_document_id is not None,
        resume_filename=resume_filename,
        org_decision=row.org_decision,
        candidate_response=row.candidate_response,
        outcome=row.outcome,
        invited_at=row.invited_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _applications_query():
    """Submission + listing + org name + CV filename, for list responses."""
    return (
        select(
            PublicInterviewSubmission,
            PublicInterview,
            Organization.name,
            CandidateDocument.filename,
        )
        .join(PublicInterview, PublicInterviewSubmission.public_id == PublicInterview.id)
        .join(Organization, PublicInterview.org_id == Organization.id)
        .outerjoin(
            CandidateDocument,
            PublicInterviewSubmission.resume_document_id == CandidateDocument.id,
        )
    )


async def _application_response_for(
    submission: PublicInterviewSubmission, pi: PublicInterview, db: AsyncSession
) -> ApplicationResponse:
    """Build a full response (org name + CV filename) for a single submission."""
    org_name = (
        await db.execute(select(Organization.name).where(Organization.id == pi.org_id))
    ).scalar_one_or_none()
    filename = None
    if submission.resume_document_id is not None:
        filename = (
            await db.execute(
                select(CandidateDocument.filename).where(
                    CandidateDocument.id == submission.resume_document_id
                )
            )
        ).scalar_one_or_none()
    return _application_response(submission, pi.title, org_name, filename)


def _normalize_email(value: Optional[str]) -> str:
    email = (value or "").strip()
    local, _, domain = email.partition("@")
    if not local or "." not in domain or " " in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid email is required")
    return email


async def _resolve_resume_document(
    profile: CandidateProfile,
    req: ApplyRequest,
    resume: Optional[UploadFile],
    authenticated: bool,
    db: AsyncSession,
) -> tuple[CandidateDocument, bool]:
    """Pick the CV for an application. Returns (document, is_new_upload).

    Guests must upload a file. Logged-in candidates may upload one, point at an
    existing document of theirs, or fall back to the CV already on their profile.
    """
    if resume is not None and (resume.filename or ""):
        return await store_candidate_resume(profile, resume, db), True

    if authenticated:
        if req.resume_document_id is not None:
            doc = (
                await db.execute(
                    select(CandidateDocument).where(
                        CandidateDocument.id == req.resume_document_id,
                        CandidateDocument.candidate_id == profile.id,
                    )
                )
            ).scalar_one_or_none()
            if doc is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resume document")
            return doc, False

        existing = await latest_resume_document(profile.id, db)
        if existing is not None:
            return existing, False

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CV is required")


async def apply_to_public_interview(
    interview_id: str,
    req: ApplyRequest,
    db: AsyncSession,
    candidate=None,
    resume: Optional[UploadFile] = None,
) -> ApplicationResponse:
    # One query for the listing and its organization name (every round trip counts
    # when the database is remote).
    row = (
        await db.execute(
            select(PublicInterview, Organization.name)
            .join(Organization, PublicInterview.org_id == Organization.id)
            .where(
                PublicInterview.id == interview_id,
                PublicInterview.is_open.is_(True),
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found or closed")
    pi, org_name = row

    authenticated = candidate is not None
    if authenticated:
        profile = candidate
    else:
        email = _normalize_email(req.candidate_email)
        name = (req.candidate_name or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required")
        profile_result = await db.execute(
            select(CandidateProfile).where(func.lower(CandidateProfile.email) == email.lower())
        )
        profile = profile_result.scalars().first()
        if profile is not None and profile.is_registered:
            # A guest must not attach a CV to (or apply as) someone's real account.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account already exists for this email. Please sign in to apply.",
            )
        if profile is None:
            profile = CandidateProfile(
                id=uuid.uuid4(),
                email=email,
                name=name,
                is_registered=False,
            )
            db.add(profile)
            await db.flush()
        else:
            profile.name = name

    document, is_new_upload = await _resolve_resume_document(profile, req, resume, authenticated, db)

    existing_result = await db.execute(
        select(PublicInterviewSubmission).where(
            PublicInterviewSubmission.public_id == pi.id,
            PublicInterviewSubmission.candidate_profile_id == profile.id,
        )
    )
    submission = existing_result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if submission is None:
        submission = PublicInterviewSubmission(
            id=uuid.uuid4(),
            created_at=now,
            updated_at=now,
            public_id=pi.id,
            candidate_profile_id=profile.id,
            resume_document_id=document.id,
            candidate_email=profile.email,
            candidate_name=profile.name,
            status="applied",
            org_decision="pending",
            candidate_response="pending",
            outcome="pending",
            fit_status="pending",
        )
        db.add(submission)
    else:
        submission.resume_document_id = document.id
        if is_new_upload:
            # A new CV invalidates any earlier fit evaluation.
            submission.fit_status = "pending"
            submission.fit_error = None

    await db.commit()
    # Everything the response needs is already in hand: no extra queries or refresh.
    return _application_response(submission, pi.title, org_name, document.filename)


async def list_org_applications(org_id: str, db: AsyncSession) -> list[ApplicationResponse]:
    result = await db.execute(
        _applications_query()
        .where(PublicInterview.org_id == org_id)
        .order_by(PublicInterviewSubmission.created_at.desc())
    )
    return [
        _application_response(submission, pi.title, org_name, filename)
        for submission, pi, org_name, filename in result.all()
    ]


async def list_candidate_applications(
    candidate_id: UUID, db: AsyncSession
) -> list[ApplicationResponse]:
    result = await db.execute(
        _applications_query()
        .where(PublicInterviewSubmission.candidate_profile_id == candidate_id)
        .order_by(PublicInterviewSubmission.created_at.desc())
    )
    return [
        _application_response(submission, pi.title, org_name, filename)
        for submission, pi, org_name, filename in result.all()
    ]


async def _get_org_application(
    application_id: str, org_id: str, db: AsyncSession
) -> tuple[PublicInterviewSubmission, PublicInterview]:
    result = await db.execute(
        select(PublicInterviewSubmission, PublicInterview)
        .join(PublicInterview, PublicInterviewSubmission.public_id == PublicInterview.id)
        .where(
            PublicInterviewSubmission.id == application_id,
            PublicInterview.org_id == org_id,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return row[0], row[1]


EVALUATION_STALE_AFTER = timedelta(minutes=5)


async def queue_application_evaluation(
    application_id: str, org_id: str, db: AsyncSession
) -> ApplicationResponse:
    """Mark an application for (re-)evaluation. The caller schedules the actual
    run as a background task after this returns."""
    submission, pi = await _get_org_application(application_id, org_id, db)
    if submission.resume_document_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application has no CV to evaluate")
    if (
        submission.fit_status == "running"
        and submission.updated_at is not None
        and datetime.now(timezone.utc) - submission.updated_at < EVALUATION_STALE_AFTER
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Evaluation is already running")
    submission.fit_status = "pending"
    submission.fit_error = None
    await db.commit()
    await db.refresh(submission)
    return await _application_response_for(submission, pi, db)


async def get_application_resume(
    application_id: str, org_id: str, db: AsyncSession
) -> tuple[str, str]:
    """(file path, download name) of an application's CV; org ownership of the
    application is enforced by ``_get_org_application``."""
    submission, _pi = await _get_org_application(application_id, org_id, db)
    document = (
        await db.get(CandidateDocument, submission.resume_document_id)
        if submission.resume_document_id
        else None
    )
    path = ((document.document_metadata or {}).get("path") if document else None)
    if not path and submission.candidate_profile_id:
        profile = await db.get(CandidateProfile, submission.candidate_profile_id)
        path = profile.resume_url if profile else None
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    resolved = Path(path).resolve()
    if not resolved.is_relative_to(RESUMES_DIR.resolve()) or not resolved.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume file not found")
    name = (document.filename if document else None) or f"{submission.candidate_name}_resume.pdf"
    return str(resolved), name


async def set_application_fit(
    application_id: str,
    req: FitScoreRequest,
    org_id: str,
    db: AsyncSession,
) -> ApplicationResponse:
    submission, pi = await _get_org_application(application_id, org_id, db)
    submission.fit_score = req.fit_score
    submission.fit_summary = req.fit_summary
    if submission.status == "applied":
        submission.status = "screening"
    await db.commit()
    await db.refresh(submission)
    return await _application_response_for(submission, pi, db)


async def invite_application(
    application_id: str,
    org_id: str,
    actor_id: Optional[str],
    db: AsyncSession,
) -> ApplicationResponse:
    submission, pi = await _get_org_application(application_id, org_id, db)
    if submission.org_decision == "rejected" or submission.outcome in {"hired", "rejected"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application is closed")
    if submission.candidate_response in {"accepted", "declined"}:
        # Re-inviting would overwrite the candidate's answer and status.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate already responded")

    if submission.session_id is None:
        session = InterviewSession(
            id=uuid.uuid4(),
            org_id=pi.org_id,
            it_role_id=pi.it_role_id,
            candidate_profile_id=submission.candidate_profile_id,
            level_code=pi.level_code,
            job_role_snapshot=pi.title,
            session_type="public",
            interaction_mode=pi.interview_mode,
            status="initiating",
            invite_token=uuid.uuid4().hex,
            invite_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(session)
        await db.flush()
        submission.session_id = session.id
    else:
        # Re-sending the invite: make sure the link is still valid.
        existing = (
            await db.execute(select(InterviewSession).where(InterviewSession.id == submission.session_id))
        ).scalar_one_or_none()
        if existing is not None:
            if not existing.invite_token:
                existing.invite_token = uuid.uuid4().hex
            existing.invite_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    now = datetime.now(timezone.utc)
    submission.org_decision = "invited"
    submission.status = "interview_offered"
    submission.invited_at = now
    submission.org_decided_by = UUID(str(actor_id)) if actor_id else None
    submission.org_decided_at = now
    await db.commit()
    await db.refresh(submission)
    return await _application_response_for(submission, pi, db)


async def _record_candidate_response(
    submission: PublicInterviewSubmission, response: str, db: AsyncSession
) -> None:
    """Apply an accept/decline to the application (and cancel the session on decline)."""
    submission.candidate_response = response
    submission.candidate_responded_at = datetime.now(timezone.utc)
    submission.status = "interview_accepted" if response == "accepted" else "interview_declined"

    if submission.session_id is not None and response == "declined":
        session = (
            await db.execute(select(InterviewSession).where(InterviewSession.id == submission.session_id))
        ).scalar_one_or_none()
        if session is not None:
            session.status = "cancelled"


async def _get_invitation(
    token: str, db: AsyncSession
) -> tuple[PublicInterviewSubmission, InterviewSession, PublicInterview, Optional[str]]:
    """Resolve an application invitation by its emailed token
    (``interview_sessions.invite_token``). The public listing token is never used here."""
    token = (token or "").strip()
    row = None
    if token:
        row = (
            await db.execute(
                select(PublicInterviewSubmission, InterviewSession, PublicInterview, Organization.name)
                .join(InterviewSession, PublicInterviewSubmission.session_id == InterviewSession.id)
                .join(PublicInterview, PublicInterviewSubmission.public_id == PublicInterview.id)
                .join(Organization, PublicInterview.org_id == Organization.id)
                .where(InterviewSession.invite_token == token)
            )
        ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    return row[0], row[1], row[2], row[3]


def _invitation_response(
    submission: PublicInterviewSubmission,
    session: InterviewSession,
    pi: PublicInterview,
    org_name: Optional[str],
) -> ApplicationInvitationResponse:
    now = datetime.now(timezone.utc)
    expired = bool(session.invite_expires_at and session.invite_expires_at < now)
    open_invite = (
        submission.org_decision == "invited"
        and submission.outcome == "pending"
        and session.status != "cancelled"
    )
    return ApplicationInvitationResponse(
        org_name=org_name,
        job_title=pi.title,
        candidate_name=submission.candidate_name,
        candidate_email=submission.candidate_email,
        status=submission.status,
        candidate_response=submission.candidate_response,
        can_respond=open_invite and submission.candidate_response == "pending" and not expired,
        expired=expired and submission.candidate_response == "pending",
        expires_at=session.invite_expires_at,
        session_id=session.id if submission.candidate_response == "accepted" and open_invite else None,
        access_token=(
            create_interview_access_token(session.id)
            if submission.candidate_response == "accepted" and open_invite
            else None
        ),
    )


async def get_application_invitation(token: str, db: AsyncSession) -> ApplicationInvitationResponse:
    submission, session, pi, org_name = await _get_invitation(token, db)
    return _invitation_response(submission, session, pi, org_name)


async def respond_to_invitation(
    token: str, response: str, db: AsyncSession
) -> ApplicationInvitationResponse:
    response = (response or "").lower()
    if response not in {"accepted", "declined"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="response must be accepted or declined")

    submission, session, pi, org_name = await _get_invitation(token, db)
    state = _invitation_response(submission, session, pi, org_name)

    if submission.candidate_response == response:
        return state  # idempotent: a double click or a reopened email link
    if submission.candidate_response != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already responded to this invitation")
    if state.expired:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This invitation has expired")
    if not state.can_respond:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This invitation is no longer active")

    await _record_candidate_response(submission, response, db)
    await db.commit()
    await db.refresh(submission)
    await db.refresh(session)
    return _invitation_response(submission, session, pi, org_name)


async def respond_to_application(
    application_id: str,
    req: CandidateResponseRequest,
    candidate_id: UUID,
    db: AsyncSession,
) -> ApplicationResponse:
    response = (req.response or "").lower()
    if response not in {"accepted", "declined"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="response must be accepted or declined")

    result = await db.execute(
        select(PublicInterviewSubmission, PublicInterview)
        .join(PublicInterview, PublicInterviewSubmission.public_id == PublicInterview.id)
        .where(
            PublicInterviewSubmission.id == application_id,
            PublicInterviewSubmission.candidate_profile_id == candidate_id,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    submission, pi = row
    if submission.org_decision != "invited":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active invitation")

    await _record_candidate_response(submission, response, db)
    await db.commit()
    await db.refresh(submission)
    return await _application_response_for(submission, pi, db)


async def set_application_outcome(
    application_id: str,
    req: ApplicationOutcomeRequest,
    org_id: str,
    actor_id: Optional[str],
    db: AsyncSession,
) -> ApplicationResponse:
    outcome = (req.outcome or "").lower()
    if outcome not in {"hired", "rejected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="outcome must be hired or rejected")

    submission, pi = await _get_org_application(application_id, org_id, db)
    now = datetime.now(timezone.utc)
    submission.outcome = outcome
    submission.status = outcome
    submission.outcome_decided_by = UUID(str(actor_id)) if actor_id else None
    submission.outcome_decided_at = now
    await db.commit()
    await db.refresh(submission)
    return await _application_response_for(submission, pi, db)
