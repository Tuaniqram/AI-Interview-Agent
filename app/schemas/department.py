from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str
    website: Optional[str] = None
    description: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: int
    org_id: Optional[UUID] = None
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
