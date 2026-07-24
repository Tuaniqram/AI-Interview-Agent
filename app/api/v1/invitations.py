from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_org_role, resolve_org_id
from app.database.deps import get_db
from app.models.db import CandidateInvitation, CandidateProfile, Department, InterviewSession, User

router = APIRouter(prefix="/invitations", tags=["invitations"])


class InvitationCreateRequest(BaseModel):
    candidate_email: str
    candidate_name: str
    job_role: str
    expires_in_days: int = 7


class InvitationResponse(BaseModel):
    id: str
    candidate_email: str
    candidate_name: str
    job_role: str
    token: str
    status: str
    expires_at: datetime
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.post("", response_model=InvitationResponse)
async def create_invitation(
    req: InvitationCreateRequest,
    org_id: str = Depends(resolve_org_id),
    user: User = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Org-Id header is required")

    department_result = await db.execute(
        select(Department).where(Department.org_id == org_id)
    )
    department = department_result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No department found for org")

    token = uuid.uuid4().hex + uuid.uuid4().hex
    invitation = CandidateInvitation(
        id=uuid.uuid4(),
        department_id=department.id,
        candidate_email=req.candidate_email,
        candidate_name=req.candidate_name,
        job_role=req.job_role,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=req.expires_in_days),
        created_by=user.id,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    return InvitationResponse(
        id=str(invitation.id),
        candidate_email=invitation.candidate_email,
        candidate_name=invitation.candidate_name,
        job_role=invitation.job_role,
        token=invitation.token,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )


@router.get("/{token}")
async def verify_invitation(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CandidateInvitation).where(
            CandidateInvitation.token == token,
            CandidateInvitation.status == "pending",
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invitation")

    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")

    department_result = await db.execute(select(Department).where(Department.id == invitation.department_id))
    department = department_result.scalar_one_or_none()

    return {
        "valid": True,
        "candidate_name": invitation.candidate_name,
        "candidate_email": invitation.candidate_email,
        "job_role": invitation.job_role,
        "department_name": department.name if department else None,
    }


@router.post("/{token}/accept")
async def accept_invitation(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CandidateInvitation).where(
            CandidateInvitation.token == token,
            CandidateInvitation.status == "pending",
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invitation")

    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")

    candidate_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.email == invitation.candidate_email)
    )
    candidate = candidate_result.scalar_one_or_none()

    if not candidate:
        candidate = CandidateProfile(
            id=uuid.uuid4(),
            email=invitation.candidate_email,
            name=invitation.candidate_name,
            is_verified=True,
            verified_at=datetime.now(timezone.utc),
        )
        db.add(candidate)
        await db.flush()

    invitation.status = "accepted"

    session = InterviewSession(
        id=uuid.uuid4(),
        candidate_profile_id=candidate.id,
        department_id=invitation.department_id,
        job_role=invitation.job_role,
        session_type="invitation",
    )
    db.add(session)
    await db.commit()

    return {
        "session_id": str(session.id),
        "candidate_id": str(candidate.id),
        "candidate_name": candidate.name,
        "candidate_email": candidate.email,
        "job_role": invitation.job_role,
    }
