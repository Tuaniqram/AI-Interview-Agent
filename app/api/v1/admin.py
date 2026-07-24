from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import AdminOrgResponse, AdminUserResponse, PlatformStatsResponse
from app.admin.service import get_platform_stats, list_orgs, list_users, suspend_org
from app.auth.middleware import authenticate
from app.database.deps import get_db
from app.models.db import User

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(user: User = Depends(authenticate)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


@router.get("/stats", response_model=PlatformStatsResponse)
async def stats_endpoint(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await get_platform_stats(db)


@router.get("/organizations", response_model=list[AdminOrgResponse])
async def list_orgs_endpoint(
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await list_orgs(search, db)


@router.post("/organizations/{org_id}/toggle-suspend")
async def toggle_suspend_endpoint(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    await suspend_org(org_id, db)
    return {"message": "Organization status toggled"}


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users_endpoint(
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await list_users(search, db)
