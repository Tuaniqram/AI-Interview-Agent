from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_org_role, require_org_role_path, resolve_org_id
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
from app.services.audit_log import AuditLogService
from app.marketplace.service import (
    create_public_interview,
    delete_public_interview,
    get_org_profile,
    get_public_interview,
    list_org_public_interviews,
    list_organizations,
    start_public_interview,
    update_public_interview,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/organizations", response_model=list[OrgListingResponse])
async def list_orgs(
    search: Optional[str] = Query(None),
    modes: Optional[str] = Query(None),
    expiry: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_organizations(search, modes, expiry, db)


@router.get("/organizations/{slug}")
async def org_profile(slug: str, db: AsyncSession = Depends(get_db)):
    return await get_org_profile(slug, db)


@router.get("/interviews/{interview_id}", response_model=PublicInterviewResponse)
async def get_interview(interview_id: str, db: AsyncSession = Depends(get_db)):
    return await get_public_interview(interview_id, db)


@router.post("/interviews/{interview_id}/start", response_model=StartInterviewResponse)
async def start_interview(
    interview_id: str,
    req: StartInterviewRequest,
    db: AsyncSession = Depends(get_db),
):
    return await start_public_interview(interview_id, req, db)


# ── Org CRUD for public interview listings ────────────────────────────


@router.post("/interviews", response_model=OrgPublicInterviewResponse)
async def create_listing(
    req: CreatePublicInterviewRequest,
    request: Request,
    org_id: str = Depends(resolve_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    return await create_public_interview(
        org_id, req, db,
        actor_id=str(request.state.user.id) if hasattr(request.state, "user") else None,
        ip_address=request.client.host if request.client else None,
    )


@router.get("/org/{org_id}/interviews", response_model=list[OrgPublicInterviewResponse])
async def list_listings(
    org_id: str,
    _: None = Depends(require_org_role_path(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    return await list_org_public_interviews(org_id, db)


@router.put("/interviews/{interview_id}", response_model=OrgPublicInterviewResponse)
async def update_listing(
    interview_id: str,
    req: UpdatePublicInterviewRequest,
    request: Request,
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await update_public_interview(interview_id, req, db)
    audit = AuditLogService(db)
    await audit.log(
        action="marketplace.update",
        resource_type="public_interview",
        resource_id=interview_id,
        user_id=str(request.state.user.id) if hasattr(request.state, "user") else None,
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.delete("/interviews/{interview_id}", status_code=204)
async def delete_listing(
    interview_id: str,
    request: Request,
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    await delete_public_interview(interview_id, db)
    audit = AuditLogService(db)
    await audit.log(
        action="marketplace.delete",
        resource_type="public_interview",
        resource_id=interview_id,
        user_id=str(request.state.user.id) if hasattr(request.state, "user") else None,
        ip_address=request.client.host if request.client else None,
    )
