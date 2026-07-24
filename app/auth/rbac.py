from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.database.deps import get_db
from app.models.db import OrgUser, User


async def resolve_org_id(
    org_id: Optional[str] = Header(None, alias="X-Org-Id"),
) -> Optional[str]:
    return org_id


def require_org_role(allowed_roles: list[str]):
    """Dependency factory: check user has an org role from X-Org-Id header.

    Usage:
        @router.get("/departments")
        async def list_departments(
            user: User = Depends(authenticate),
            _: None = Depends(require_org_role(["owner", "member", "viewer"])),
        ):
    """
    async def _check(
        user: User = Depends(authenticate),
        org_id: Optional[str] = Depends(resolve_org_id),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        if user.is_admin:
            return
        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Org-Id header is required",
            )
        result = await db.execute(
            select(OrgUser).where(
                OrgUser.org_id == org_id,
                OrgUser.user_id == user.id,
            )
        )
        ou = result.scalar_one_or_none()
        if not ou or ou.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this organization",
            )

    return _check


def require_org_role_path(allowed_roles: list[str]):
    """Dependency factory: check user has an org role via path param ``org_id``.

    Usage:
        @router.patch("/orgs/{org_id}")
        async def update_org(
            org_id: UUID,
            req: OrganizationUpdate,
            user: User = Depends(authenticate),
            _: None = Depends(require_org_role_path(["owner"])),
        ):
    """
    async def _check(
        org_id: UUID,
        user: User = Depends(authenticate),
        request: Request = None,
        db: AsyncSession = Depends(get_db),
    ) -> None:
        if user.is_admin:
            return
        target_org = org_id
        if not target_org:
            target_org = request.path_params.get("org_id")
        result = await db.execute(
            select(OrgUser).where(
                OrgUser.org_id == target_org,
                OrgUser.user_id == user.id,
            )
        )
        ou = result.scalar_one_or_none()
        if not ou or ou.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this organization",
            )

    return _check


async def require_admin(user: User = Depends(authenticate)) -> User:
    """Dependency: user must be a system admin (``is_admin=True``)."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
