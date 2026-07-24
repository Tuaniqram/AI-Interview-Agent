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
    Organization,
    PublicInterview,
    PublicInterviewSubmission,
)
from app.services.audit_log import AuditLogService
from app.services.marketplace_generator import generate_rich_description


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
        select(PublicInterview).where(
            PublicInterview.org_id == org.id,
            PublicInterview.is_open == True,
            (PublicInterview.starts_at == None) | (PublicInterview.starts_at <= now),
            (PublicInterview.expires_at == None) | (PublicInterview.expires_at > now),
        )
    )
    interviews = []
    for pi in interviews_result.scalars().all():
        dept_name = ""
        if pi.department_id:
            dept_result = await db.execute(
                select(Department).where(Department.id == pi.department_id)
            )
            dept = dept_result.scalar_one_or_none()
            dept_name = dept.name if dept else ""

        interviews.append(
            PublicInterviewResponse(
                id=pi.id,
                org_id=pi.org_id,
                title=pi.title,
                description=pi.description,
                rich_description=pi.rich_description,
                interview_mode=pi.interview_mode,
                org_name=org.name,
                department_name=dept_name,
                skills_required=pi.skills_required,
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

    session = InterviewSession(
        id=uuid.uuid4(),
        org_id=pi.org_id,
        department_id=pi.department_id,
        candidate_profile_id=None,
        job_role=pi.title,
        session_type="public",
        interaction_mode=pi.interview_mode,
    )

    # G4: link to existing candidate profile if email matches
    candidate_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.email == req.candidate_email).limit(1)
    )
    candidate = candidate_result.scalar_one_or_none()
    if candidate:
        session.candidate_profile_id = candidate.id

    db.add(session)
    await db.flush()

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
        select(PublicInterview)
        .where(PublicInterview.org_id == org_id)
        .order_by(PublicInterview.created_at.desc())
    )
    items = []
    for pi in result.scalars().all():
        dept_name = ""
        if pi.department_id:
            dept_result = await db.execute(
                select(Department).where(Department.id == pi.department_id)
            )
            dept = dept_result.scalar_one_or_none()
            dept_name = dept.name if dept else ""
        resp = OrgPublicInterviewResponse.model_validate(pi)
        resp.department_name = dept_name
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
