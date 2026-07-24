from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class OrgListingResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    interview_count: int = 0

    model_config = {"from_attributes": True}


class PublicInterviewResponse(BaseModel):
    id: UUID
    org_id: UUID
    title: str
    description: Optional[str] = None
    rich_description: Optional[str] = None
    interview_mode: str
    org_name: Optional[str] = None
    department_name: Optional[str] = None
    skills_required: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrgPublicInterviewResponse(BaseModel):
    id: UUID
    org_id: UUID
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    rich_description: Optional[str] = None
    interview_mode: str
    is_open: bool
    token: str
    max_candidates: Optional[int] = None
    token_expires_at: Optional[datetime] = None
    skills_required: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CreatePublicInterviewRequest(BaseModel):
    title: str
    department_id: int
    description: Optional[str] = None
    interview_mode: str = "typing"
    max_candidates: Optional[int] = None
    skills_required: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class UpdatePublicInterviewRequest(BaseModel):
    title: Optional[str] = None
    department_id: Optional[int] = None
    description: Optional[str] = None
    interview_mode: Optional[str] = None
    is_open: Optional[bool] = None
    max_candidates: Optional[int] = None
    skills_required: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class StartInterviewRequest(BaseModel):
    candidate_email: str
    candidate_name: str


class StartInterviewResponse(BaseModel):
    session_id: UUID
    token: str
