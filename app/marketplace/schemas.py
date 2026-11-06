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
    it_role_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    rich_description: Optional[str] = None
    interview_mode: str
    org_name: Optional[str] = None
    department_name: Optional[str] = None
    skills_required: Optional[str] = None
    style_name: Optional[str] = "STANDARD"
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrgPublicInterviewResponse(BaseModel):
    id: UUID
    org_id: UUID
    it_role_id: UUID
    level_code: Optional[str] = None
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
    style_name: Optional[str] = "STANDARD"
    template_id: Optional[UUID] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CreatePublicInterviewRequest(BaseModel):
    title: str
    it_role_id: UUID
    level_code: Optional[str] = None
    description: Optional[str] = None
    interview_mode: str = "typing"
    max_candidates: Optional[int] = None
    skills_required: Optional[str] = None
    style_name: str = "STANDARD"
    template_id: Optional[UUID] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class UpdatePublicInterviewRequest(BaseModel):
    title: Optional[str] = None
    it_role_id: Optional[UUID] = None
    level_code: Optional[str] = None
    description: Optional[str] = None
    interview_mode: Optional[str] = None
    is_open: Optional[bool] = None
    max_candidates: Optional[int] = None
    skills_required: Optional[str] = None
    style_name: Optional[str] = None
    template_id: Optional[UUID] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class StartInterviewRequest(BaseModel):
    candidate_email: str
    candidate_name: str


class StartInterviewResponse(BaseModel):
    session_id: UUID
    token: str


class ApplyRequest(BaseModel):
    candidate_email: str
    candidate_name: str
    resume_document_id: Optional[UUID] = None


class ApplicationResponse(BaseModel):
    id: UUID
    public_id: UUID
    public_title: Optional[str] = None
    org_name: Optional[str] = None
    session_id: Optional[UUID] = None
    candidate_profile_id: Optional[UUID] = None
    resume_document_id: Optional[UUID] = None
    candidate_email: str
    candidate_name: str
    status: str
    fit_score: Optional[float] = None
    fit_summary: Optional[str] = None
    org_decision: str
    candidate_response: str
    outcome: str
    invited_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FitScoreRequest(BaseModel):
    fit_score: float
    fit_summary: Optional[str] = None


class CandidateResponseRequest(BaseModel):
    response: str


class ApplicationOutcomeRequest(BaseModel):
    outcome: str
