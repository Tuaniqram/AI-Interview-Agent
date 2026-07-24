from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import AuditLog


async def log(
    db: AsyncSession,
    action: str,
    org_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    entry = AuditLog(
        id=uuid.uuid4(),
        org_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
