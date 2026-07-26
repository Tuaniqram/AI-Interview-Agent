from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_admin, require_org_role_path
from app.database.deps import get_db
from app.models.db import Department, InterviewTemplate, Organization, User, ScorecardTemplate, ScorecardResult
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
from app.orgs.service import (
    accept_org_invitation,
    add_member,
    add_member_by_email,
    create_org,
    get_org,
    invite_member,
    list_members,
    remove_member,
    update_member_role,
    update_org,
    verify_org_invitation,
)

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.post("", response_model=OrganizationResponse)
async def create_org_endpoint(
    req: OrganizationCreate,
    user: User = Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    return await create_org(req, user, db)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_org_endpoint(
    org_id: UUID,
    user: User = Depends(authenticate),
    _: None = Depends(require_org_role_path(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    return await get_org(org_id, db)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_org_endpoint(
    org_id: UUID,
    req: OrganizationUpdate,
    user: User = Depends(authenticate),
    _: None = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    return await update_org(org_id, req, user, db)


@router.get("/{org_id}/members", response_model=list[OrgMemberResponse])
async def list_members_endpoint(
    org_id: UUID,
    user: User = Depends(authenticate),
    _: None = Depends(require_org_role_path(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    return await list_members(org_id, db)


@router.post("/{org_id}/members", response_model=OrgMemberResponse)
async def add_member_endpoint(
    org_id: UUID,
    req: AddMemberRequest,
    user: User = Depends(authenticate),
    _: None = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    return await add_member(org_id, req, user, db)


@router.post("/{org_id}/members/by-email", response_model=OrgMemberResponse)
async def add_member_by_email_endpoint(
    org_id: UUID,
    req: AddMemberByEmailRequest,
    user: User = Depends(authenticate),
    _: None = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    return await add_member_by_email(org_id, req, user, db)


@router.patch("/{org_id}/members/{member_id}", response_model=OrgMemberResponse)
async def update_member_role_endpoint(
    org_id: UUID,
    member_id: UUID,
    req: UpdateMemberRoleRequest,
    user: User = Depends(authenticate),
    _: None = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    return await update_member_role(org_id, member_id, req, user, db)


@router.delete("/{org_id}/members/{member_id}", status_code=204)
async def remove_member_endpoint(
    org_id: UUID,
    member_id: UUID,
    user: User = Depends(authenticate),
    _: None = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    await remove_member(org_id, member_id, user, db)


@router.get("/{org_id}/templates")
async def list_org_templates(
    org_id: UUID,
    department_id: int | None = None,
    _: User = Depends(require_org_role_path(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(InterviewTemplate, Department.name.label("department_name"))
        .join(Department, InterviewTemplate.department_id == Department.id)
        .where(Department.org_id == org_id)
        .order_by(InterviewTemplate.created_at.desc())
    )
    if department_id is not None:
        query = query.where(InterviewTemplate.department_id == department_id)

    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "id": str(t.id),
            "department_id": t.department_id,
            "department_name": dept_name,
            "name": t.name,
            "job_role": t.job_role,
            "description": t.description,
            "interview_style": t.interview_style,
            "competencies": t.competencies,
            "total_questions": t.total_questions,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t, dept_name in rows
    ]


@router.post("/{org_id}/invite", response_model=InviteMemberResponse)
async def invite_member_endpoint(
    org_id: UUID,
    req: InviteMemberRequest,
    user: User = Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    return await invite_member(org_id, req, user, db)


@router.get("/invitations/{token}", response_model=OrgInvitationVerifyResponse)
async def verify_org_invitation_endpoint(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    return await verify_org_invitation(token, db)


@router.post("/invitations/{token}/accept", response_model=OrgMemberResponse)
async def accept_org_invitation_endpoint(
    token: str,
    user: User = Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    return await accept_org_invitation(token, user, db)
