from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_org_role_path
from app.database.deps import get_db
from app.models.db import AuditLog, User

router = APIRouter(prefix="/orgs/{org_id}/audit-logs", tags=["audit-logs"])


@router.get("")
async def list_audit_logs(
    org_id: UUID,
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AuditLog)
        .where(AuditLog.org_id == org_id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(limit)
    )
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
