from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PlatformStatsResponse(BaseModel):
    total_orgs: int = 0
    total_users: int = 0
    total_interviews: int = 0
    total_departments: int = 0
    active_sessions: int = 0


class AdminOrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    member_count: int = 0
    interview_count: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminUserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
