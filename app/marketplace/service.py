from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.deps import get_db
from app.marketplace.schemas import (
    CreatePublicInterviewRequest,
    OrgListingResponse,
    OrgPublicInterviewResponse,
    PublicInterviewResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    UpdatePublicInterviewRequest,
)
from app.models.db import (
    CandidateProfile,
    Department,
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
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY


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
            Department.name.label("dept_name"),
        ).outerjoin(
            Department, PublicInterview.department_id == Department.id
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
    if pi.department_id:
        dept_result = await db.execute(
            select(Department).where(Department.id == pi.department_id)
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
        department_id=pi.department_id,
        candidate_profile_id=None,
        job_role=pi.title,
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

    # Seed v4 state with the listing's style and candidate profile data
    style = get_style(pi.style_name or "STANDARD")
    store = get_v4_session_store()
    state = {
        "session_id": str(session.id),
        "job_role": pi.title or "Software Engineer",
        "department_id": pi.department_id,
        "interview_style": style,
        "persona": style.get("persona", "friendly"),
        "difficulty_level": style.get("difficulty_range", (1, 3))[0],
        "candidate_profile": {
            "full_name": req.candidate_name or "Candidate",
            "headline": "",
            "strengths": list(profile_data.get("strengths", [])) if profile_data else [],
            "weaknesses": list(profile_data.get("weaknesses", [])) if profile_data else [],
        },
        "required_competencies": [c["id"] for c in COMPETENCY_TAXONOMY],
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

    token = uuid.uuid4().hex
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
        department_id=req.department_id,
        title=req.title,
        description=req.description,
        interview_mode=req.interview_mode,
        max_candidates=req.max_candidates,
        skills_required=req.skills_required,
        style_name=req.style_name,
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
        details={"title": req.title, "department_id": req.department_id, "interview_mode": req.interview_mode},
        ip_address=ip_address,
    )

    # Build response with department name
    dept_name = ""
    if pi.department_id:
        dept_result = await db.execute(
            select(Department).where(Department.id == pi.department_id)
        )
        dept = dept_result.scalar_one_or_none()
        dept_name = dept.name if dept else ""

    resp = OrgPublicInterviewResponse.model_validate(pi)
    resp.department_name = dept_name
    return resp


async def list_org_public_interviews(
    org_id: str,
    db: AsyncSession,
) -> list[OrgPublicInterviewResponse]:
    result = await db.execute(
        select(
            PublicInterview,
            Department.name.label("dept_name"),
        ).outerjoin(
            Department, PublicInterview.department_id == Department.id
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
    await db.commit()
    await db.refresh(pi)

    # Regenerate description if title or skills changed
    if title_changed:
        asyncio.create_task(generate_rich_description(str(pi.id)))

    dept_name = ""
    if pi.department_id:
        dept_result = await db.execute(
            select(Department).where(Department.id == pi.department_id)
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
