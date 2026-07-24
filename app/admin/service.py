from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import AdminOrgResponse, AdminUserResponse, PlatformStatsResponse
from app.database.deps import get_db
from app.models.db import InterviewSession, Organization, OrgUser, User


async def get_platform_stats(db: AsyncSession) -> PlatformStatsResponse:
    org_count = await db.scalar(select(func.count(Organization.id)))
    user_count = await db.scalar(select(func.count(User.id)))
    interview_count = await db.scalar(select(func.count(InterviewSession.id)))
    active_sessions = await db.scalar(
        select(func.count(InterviewSession.id)).where(InterviewSession.status == "active")
    )

    return PlatformStatsResponse(
        total_orgs=org_count or 0,
        total_users=user_count or 0,
        total_interviews=interview_count or 0,
        active_sessions=active_sessions or 0,
    )


async def list_orgs(
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[AdminOrgResponse]:
    query = select(
        Organization.id,
        Organization.name,
        Organization.slug,
        Organization.is_active,
        Organization.created_at,
        func.count(func.distinct(OrgUser.id)).label("member_count"),
        func.count(func.distinct(InterviewSession.id)).label("interview_count"),
    ).outerjoin(
        OrgUser, OrgUser.org_id == Organization.id
    ).outerjoin(
        InterviewSession, InterviewSession.org_id == Organization.id
    ).group_by(Organization.id).order_by(Organization.created_at.desc())

    if search:
        query = query.where(Organization.name.ilike(f"%{search}%"))

    result = await db.execute(query)
    return [
        AdminOrgResponse(
            id=row.id,
            name=row.name,
            slug=row.slug,
            is_active=row.is_active,
            member_count=row.member_count or 0,
            interview_count=row.interview_count or 0,
            created_at=row.created_at,
        )
        for row in result.all()
    ]


async def suspend_org(org_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    org.is_active = not org.is_active
    await db.commit()


async def list_users(
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserResponse]:
    query = select(User).order_by(User.created_at.desc())
    if search:
        query = query.where(
            User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )
    result = await db.execute(query)
    return [AdminUserResponse.model_validate(u) for u in result.scalars().all()]
