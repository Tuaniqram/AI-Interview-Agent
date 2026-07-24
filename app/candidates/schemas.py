from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CandidateRegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class CandidateLoginRequest(BaseModel):
    email: str
    password: str


class CandidateTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CandidateRefreshRequest(BaseModel):
    refresh_token: str


class CandidateProfileResponse(BaseModel):
    id: UUID
    email: str
    name: str
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    is_registered: bool
    is_verified: bool
    skills: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CandidateAuthResponse(BaseModel):
    candidate: CandidateProfileResponse
    tokens: CandidateTokenResponse


class CandidateUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    skills: Optional[str] = None


class CandidateInterviewResponse(BaseModel):
    id: UUID
    job_role: str
    session_type: str
    interaction_mode: Optional[str] = None
    status: Optional[str] = None
    final_score: Optional[float] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    department_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PracticeStartRequest(BaseModel):
    job_role: str = "Software Engineer"
    difficulty: str = "mid"
    tech_stack: Optional[str] = None
    num_questions: int = 5


class PracticeStartResponse(BaseModel):
    session_id: UUID
    job_role: str
    total_questions: int


class GoogleAuthRequest(BaseModel):
    credential: str
