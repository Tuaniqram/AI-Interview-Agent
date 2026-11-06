from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Organization, User
from app.orgs.schemas import (
    AddMemberByEmailRequest,
    AddMemberRequest,
    InviteMemberRequest,
    OrgMemberResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    UpdateMemberRoleRequest,
)


def _single_user_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Single-user organization: teammate management is disabled",
    )


async def create_org(req: OrganizationCreate, user: User, db: AsyncSession) -> OrganizationResponse:
    existing = await db.execute(select(Organization).where(Organization.slug == req.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already taken")

    org = Organization(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        **req.model_dump(),
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)

    return OrganizationResponse.model_validate(org)


async def get_org(org_id: UUID, db: AsyncSession) -> OrganizationResponse:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


async def get_org_by_slug(slug: str, db: AsyncSession) -> OrganizationResponse:
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


async def update_org(org_id: UUID, req: OrganizationUpdate, user: User, db: AsyncSession) -> OrganizationResponse:
    await _require_org_role(org_id, user.id, ["owner"], db)

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)
    return OrganizationResponse.model_validate(org)


async def list_members(org_id: UUID, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[OrgMemberResponse]:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    owner_result = await db.execute(select(User).where(User.id == org.owner_user_id))
    owner = owner_result.scalar_one_or_none()
    if not owner:
        return []

    return [
        OrgMemberResponse(
            id=owner.id,
            user_id=owner.id,
            email=owner.email,
            name=owner.name,
            role="owner",
            joined_at=org.created_at,
        )
    ]


async def add_member(org_id: UUID, req: AddMemberRequest, user: User, db: AsyncSession) -> OrgMemberResponse:
    raise _single_user_error()


async def add_member_by_email(
    org_id: UUID, req: AddMemberByEmailRequest, user: User, db: AsyncSession
) -> OrgMemberResponse:
    raise _single_user_error()


async def remove_member(org_id: UUID, member_id: UUID, user: User, db: AsyncSession) -> None:
    raise _single_user_error()


async def update_member_role(
    org_id: UUID,
    member_user_id: UUID,
    req: UpdateMemberRoleRequest,
    actor: User,
    db: AsyncSession,
) -> OrgMemberResponse:
    raise _single_user_error()


async def invite_member(org_id: UUID, req: InviteMemberRequest, user: User, db: AsyncSession):
    raise _single_user_error()


async def verify_org_invitation(token: str, db: AsyncSession):
    raise _single_user_error()


async def accept_org_invitation(token: str, user: User, db: AsyncSession) -> OrgMemberResponse:
    raise _single_user_error()


async def _require_org_role(org_id: UUID, user_id: UUID, allowed_roles: list[str], db: AsyncSession) -> None:
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.owner_user_id == user_id,
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this organization",
        )
