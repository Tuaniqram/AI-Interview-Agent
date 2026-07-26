from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CompetencyDef(BaseModel):
    id: str
    name: str
    category: str = "general"
    weight: float = 1.0
    max_score: float = 10.0


class ScorecardTemplateCreate(BaseModel):
    name: str
    competencies: list[CompetencyDef]


class ScorecardTemplateUpdate(BaseModel):
    name: Optional[str] = None
    competencies: Optional[list[CompetencyDef]] = None


class ScorecardTemplateResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    competencies: list[CompetencyDef]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScorecardResultResponse(BaseModel):
    id: UUID
    session_id: UUID
    template_id: Optional[UUID] = None
    scores: dict
    weighted_score: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
