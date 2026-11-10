from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_org_role_path
from app.database.deps import get_db
from app.models.db import User
from app.orgs.schemas import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrgMemberResponse,
)
from app.orgs.service import (
    create_org,
    get_org,
    list_members,
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
    _: None = Depends(require_org_role_path(["owner"])),
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
    _: None = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    return await list_members(org_id, db, skip=skip, limit=limit)
