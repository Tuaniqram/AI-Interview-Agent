from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.deps import get_db
from app.models.db import Organization, OrgInvitation, OrgUser, User
from app.orgs.schemas import (
    AddMemberByEmailRequest,
    AddMemberRequest,
    InviteMemberRequest,
    InviteMemberResponse,
    OrgInvitationVerifyResponse,
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


async def add_member_by_email(
    org_id: UUID, req: AddMemberByEmailRequest, user: User, db: AsyncSession
) -> OrgMemberResponse:
    await _require_org_role(org_id, user.id, ["owner"], db)

    user_result = await db.execute(select(User).where(User.email == req.email))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with that email. They must register first.",
        )

    existing = await db.execute(
        select(OrgUser).where(OrgUser.org_id == org_id, OrgUser.user_id == target_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already a member")

    ou = OrgUser(
        id=uuid.uuid4(),
        org_id=org_id,
        user_id=target_user.id,
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


async def invite_member(
    org_id: UUID, req: InviteMemberRequest, user: User, db: AsyncSession
) -> InviteMemberResponse:
    await _require_org_role(org_id, user.id, ["owner"], db)

    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    existing_user = await db.execute(select(User).where(User.email == req.email))
    target_user = existing_user.scalar_one_or_none()
    if target_user:
        already = await db.execute(
            select(OrgUser).where(OrgUser.org_id == org_id, OrgUser.user_id == target_user.id)
        )
        if already.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member")

    pending = await db.execute(
        select(OrgInvitation).where(
            OrgInvitation.org_id == org_id,
            OrgInvitation.email == req.email,
            OrgInvitation.status == "pending",
        )
    )
    if pending.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email",
        )

    token = secrets.token_urlsafe(32)
    invitation = OrgInvitation(
        id=uuid.uuid4(),
        org_id=org_id,
        inviter_id=user.id,
        email=req.email,
        role=req.role,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    from app.services.email import send_email
    accept_url = f"{settings.APP_URL}/accept-org-invite/{invitation.token}"
    await send_email(
        to=invitation.email,
        subject=f"Join {org.name} on AI Interview Agent",
        template_name="org_invitation.html",
        INVITER_NAME=user.name,
        ORG_NAME=org.name,
        ROLE=invitation.role,
        ACCEPT_URL=accept_url,
        APP_URL=settings.APP_URL,
    )

    return InviteMemberResponse.model_validate(invitation)


async def verify_org_invitation(token: str, db: AsyncSession) -> OrgInvitationVerifyResponse:
    result = await db.execute(
        select(OrgInvitation).where(
            OrgInvitation.token == token,
            OrgInvitation.status == "pending",
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invitation")

    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")

    org_result = await db.execute(select(Organization).where(Organization.id == invitation.org_id))
    org = org_result.scalar_one_or_none()
    inviter_result = await db.execute(select(User).where(User.id == invitation.inviter_id))
    inviter = inviter_result.scalar_one_or_none()

    return OrgInvitationVerifyResponse(
        valid=True,
        org_name=org.name if org else "Unknown",
        org_slug=org.slug if org else "",
        inviter_name=inviter.name if inviter else "Someone",
        email=invitation.email,
        role=invitation.role,
    )


async def accept_org_invitation(token: str, user: User, db: AsyncSession) -> OrgMemberResponse:
    result = await db.execute(
        select(OrgInvitation).where(
            OrgInvitation.token == token,
            OrgInvitation.status == "pending",
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invitation")

    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")

    if invitation.email != user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address",
        )

    existing = await db.execute(
        select(OrgUser).where(OrgUser.org_id == invitation.org_id, OrgUser.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        invitation.status = "accepted"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You are already a member")

    ou = OrgUser(
        id=uuid.uuid4(),
        org_id=invitation.org_id,
        user_id=user.id,
        role=invitation.role,
        invited_by=invitation.inviter_id,
    )
    db.add(ou)
    invitation.status = "accepted"
    await db.commit()
    await db.refresh(ou)

    return OrgMemberResponse(
        id=ou.id,
        user_id=user.id,
        email=user.email,
        name=user.name,
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
