from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.deps import get_db
from app.models.db import Organization, OrgUser, User
from app.orgs.schemas import (
    AddMemberRequest,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrgMemberResponse,
    UpdateMemberRoleRequest,
)


async def create_org(req: OrganizationCreate, user: User, db: AsyncSession) -> OrganizationResponse:
    existing = await db.execute(select(Organization).where(Organization.slug == req.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already taken")

    org = Organization(id=uuid.uuid4(), **req.model_dump())
    db.add(org)
    await db.flush()

    membership = OrgUser(
        id=uuid.uuid4(),
        org_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)
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


async def list_members(org_id: UUID, db: AsyncSession) -> list[OrgMemberResponse]:
    result = await db.execute(
        select(OrgUser, User)
        .join(User, OrgUser.user_id == User.id)
        .where(OrgUser.org_id == org_id)
    )
    members = []
    for ou, u in result.all():
        members.append(OrgMemberResponse(
            id=ou.id,
            user_id=ou.user_id,
            email=u.email,
            name=u.name,
            role=ou.role,
            joined_at=ou.joined_at,
        ))
    return members


async def add_member(org_id: UUID, req: AddMemberRequest, user: User, db: AsyncSession) -> OrgMemberResponse:
    await _require_org_role(org_id, user.id, ["owner"], db)

    existing = await db.execute(
        select(OrgUser).where(OrgUser.org_id == org_id, OrgUser.user_id == req.user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already a member")

    user_result = await db.execute(select(User).where(User.id == req.user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    ou = OrgUser(
        id=uuid.uuid4(),
        org_id=org_id,
        user_id=req.user_id,
        role=req.role,
        invited_by=user.id,
    )
    db.add(ou)
    await db.commit()
    await db.refresh(ou)

    return OrgMemberResponse(
        id=ou.id,
        user_id=target_user.id,
        email=target_user.email,
        name=target_user.name,
        role=ou.role,
        joined_at=ou.joined_at,
    )


async def remove_member(org_id: UUID, member_id: UUID, user: User, db: AsyncSession) -> None:
    await _require_org_role(org_id, user.id, ["owner"], db)

    result = await db.execute(
        select(OrgUser).where(OrgUser.id == member_id, OrgUser.org_id == org_id)
    )
    ou = result.scalar_one_or_none()
    if not ou:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if ou.role == "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot remove the owner")

    await db.delete(ou)
    await db.commit()


async def update_member_role(
    org_id: UUID,
    member_user_id: UUID,
    req: UpdateMemberRoleRequest,
    actor: User,
    db: AsyncSession,
) -> OrgMemberResponse:
    await _require_org_role(org_id, actor.id, ["owner"], db)

    result = await db.execute(
        select(OrgUser, User)
        .join(User, OrgUser.user_id == User.id)
        .where(OrgUser.org_id == org_id, OrgUser.user_id == member_user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    ou, target_user = row

    if ou.role == "owner":
        raise HTTPException(status_code=403, detail="Cannot change the owner's role")

    ou.role = req.role
    await db.commit()
    await db.refresh(ou)

    return OrgMemberResponse(
        id=ou.id,
        user_id=target_user.id,
        email=target_user.email,
        name=target_user.name,
        role=ou.role,
        joined_at=ou.joined_at,
    )


async def _require_org_role(org_id: UUID, user_id: UUID, allowed_roles: list[str], db: AsyncSession) -> None:
    result = await db.execute(
        select(OrgUser).where(
            OrgUser.org_id == org_id,
            OrgUser.user_id == user_id,
        )
    )
    ou = result.scalar_one_or_none()
    if not ou or ou.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this organization",
        )
