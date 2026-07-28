import json
import logging
import uuid
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import AuditLog

logger = logging.getLogger("audit")


def _to_uuid(val: str | None) -> UUID | None:
    if val is None:
        return None
    try:
        return UUID(val)
    except ValueError:
        return None


class AuditLogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        *,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        self.db.add(AuditLog(
            id=uuid.uuid4(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=_to_uuid(user_id),
            org_id=_to_uuid(org_id),
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
        ))
        await self.db.flush()
