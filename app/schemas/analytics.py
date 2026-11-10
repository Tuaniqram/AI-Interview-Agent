from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    total_it_roles: int = 0
    total_sessions: int = 0
    active_sessions: int = 0
    completed_sessions: int = 0
    average_score: Optional[float] = None
    completion_rate: float = 0


class ScoreTrendPoint(BaseModel):
    date: str
    avg_score: float
    count: int


class DistributionBucket(BaseModel):
    range: str
    count: int


class ItRoleSessionSummary(BaseModel):
    it_role_id: UUID
    name: str
    session_count: int
    avg_score: Optional[float] = None


class RoleSessionSummary(BaseModel):
    job_role: str
    count: int
    avg_score: Optional[float] = None
