from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_admin, require_org_role_path
from app.database.deps import get_db
from app.models.db import User
from app.orgs.schemas import (
    AddMemberRequest,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrgMemberResponse,
    UpdateMemberRoleRequest,
)
from app.orgs.service import (
    add_member,
    create_org,
    get_org,
    list_members,
    remove_member,
    update_member_role,
    update_org,
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
