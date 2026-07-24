from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    website: Optional[str] = None
    description: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AddMemberRequest(BaseModel):
    user_id: UUID
    role: str = "member"


class UpdateMemberRoleRequest(BaseModel):
    role: str


class OrgMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    name: str
    role: str
    joined_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
