from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import AdminOrgResponse, AdminUserResponse, PlatformStatsResponse
from app.database.deps import get_db
from app.models.db import InterviewSession, Organization, User

# Candidates are rows of `users` too. The admin pages are about hiring-side accounts: an admin, or the owner of an organization.
_HIRING_ACCOUNT = or_(User.is_admin.is_(True), exists().where(Organization.owner_user_id == User.id))


async def get_platform_stats(db: AsyncSession) -> PlatformStatsResponse:
    org_count = await db.scalar(select(func.count(Organization.id)))
    user_count = await db.scalar(select(func.count(User.id)).where(_HIRING_ACCOUNT))
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
        User.name.label("owner_name"),
        User.email.label("owner_email"),
        func.count(func.distinct(InterviewSession.id)).label("interview_count"),
    ).outerjoin(
        User, User.id == Organization.owner_user_id
    ).outerjoin(
        InterviewSession, InterviewSession.org_id == Organization.id
    ).group_by(
        Organization.id, User.name, User.email
    ).order_by(Organization.created_at.desc())

    if search:
        query = query.where(Organization.name.ilike(f"%{search}%"))

    result = await db.execute(query)
    return [
        AdminOrgResponse(
            id=row.id,
            name=row.name,
            slug=row.slug,
            is_active=row.is_active,
            owner_name=row.owner_name,
            owner_email=row.owner_email,
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
    query = (
        select(User, Organization.name.label("org_name"))
        .outerjoin(Organization, Organization.owner_user_id == User.id)
        .where(_HIRING_ACCOUNT)
        .order_by(User.created_at.desc())
    )
    if search:
        query = query.where(
            User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )
    result = await db.execute(query)
    return [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            is_active=u.is_active,
            is_admin=u.is_admin,
            org_name=org_name,
            created_at=u.created_at,
        )
        for u, org_name in result.all()
    ]
