import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_org_role_path
from app.database.deps import get_db
from app.models.db import (
    CandidateProfile,
    EvidenceStore,
    InterviewSession,
    Organization,
    ScorecardResult,
    ScorecardTemplate,
    User,
)
from app.scorecards.schemas import (
    CompetencyDef,
    ScorecardResultListItem,
    ScorecardTemplateCreate,
    ScorecardTemplateResponse,
    ScorecardTemplateUpdate,
    ScorecardResultResponse,
)
from app.scorecards.service import calculate_scorecard_for_session

router = APIRouter(prefix="/orgs/{org_id}/scorecards", tags=["scorecards"])


@router.get("", response_model=list[ScorecardTemplateResponse])
async def list_scorecards(
    org_id: UUID,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScorecardTemplate)
        .where(ScorecardTemplate.org_id == org_id)
        .order_by(ScorecardTemplate.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ScorecardTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_scorecard(
    org_id: UUID,
    req: ScorecardTemplateCreate,
    _: User = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    template = ScorecardTemplate(
        id=uuid.uuid4(),
        org_id=org_id,
        name=req.name,
        competencies=[c.model_dump() for c in req.competencies],
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/results", response_model=list[ScorecardResultListItem])
async def list_scorecard_results(
    org_id: UUID,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    """Weighted scorecard results for the organization, newest first."""
    rows = (await db.execute(
        select(
            ScorecardResult,
            ScorecardTemplate.name,
            CandidateProfile.name,
            CandidateProfile.email,
            InterviewSession.job_role_snapshot,
            InterviewSession.status,
        )
        .join(InterviewSession, ScorecardResult.session_id == InterviewSession.id)
        .outerjoin(ScorecardTemplate, ScorecardResult.template_id == ScorecardTemplate.id)
        .outerjoin(CandidateProfile, InterviewSession.candidate_profile_id == CandidateProfile.id)
        .where(InterviewSession.org_id == org_id)
        .order_by(ScorecardResult.created_at.desc())
        .limit(100)
    )).all()
    return [
        ScorecardResultListItem(
            id=result.id,
            session_id=result.session_id,
            template_id=result.template_id,
            template_name=template_name,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            job_role=job_role,
            session_status=session_status,
            weighted_score=float(result.weighted_score) if result.weighted_score is not None else None,
            created_at=result.created_at,
        )
        for result, template_name, candidate_name, candidate_email, job_role, session_status in rows
    ]


@router.get("/{template_id}", response_model=ScorecardTemplateResponse)
async def get_scorecard(
    org_id: UUID,
    template_id: UUID,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScorecardTemplate).where(
            ScorecardTemplate.id == template_id,
            ScorecardTemplate.org_id == org_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")
    return template


@router.put("/{template_id}", response_model=ScorecardTemplateResponse)
async def update_scorecard(
    org_id: UUID,
    template_id: UUID,
    req: ScorecardTemplateUpdate,
    _: User = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScorecardTemplate).where(
            ScorecardTemplate.id == template_id,
            ScorecardTemplate.org_id == org_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")
    if req.name is not None:
        template.name = req.name
    if req.competencies is not None:
        template.competencies = [c.model_dump() for c in req.competencies]
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scorecard(
    org_id: UUID,
    template_id: UUID,
    _: User = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScorecardTemplate).where(
            ScorecardTemplate.id == template_id,
            ScorecardTemplate.org_id == org_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")
    await db.delete(template)
    await db.commit()


@router.post("/{template_id}/sessions/{session_id}/calculate", response_model=ScorecardResultResponse)
async def calculate_scorecard(
    org_id: UUID,
    template_id: UUID,
    session_id: UUID,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    result = await calculate_scorecard_for_session(db, session_id, template_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard or session not found")
    return result


@router.get("/sessions/{session_id}", response_model=ScorecardResultResponse | None)
async def get_session_scorecard(
    org_id: UUID,
    session_id: UUID,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScorecardResult).where(ScorecardResult.session_id == session_id)
    )
    return result.scalar_one_or_none()
