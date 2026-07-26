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
    ScorecardTemplateCreate,
    ScorecardTemplateResponse,
    ScorecardTemplateUpdate,
    ScorecardResultResponse,
)

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
    template_result = await db.execute(
        select(ScorecardTemplate).where(
            ScorecardTemplate.id == template_id,
            ScorecardTemplate.org_id == org_id,
        )
    )
    template = template_result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")

    session_result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    ev_result = await db.execute(
        select(EvidenceStore).where(EvidenceStore.session_id == session_id)
    )
    evidence = ev_result.scalars().all()

    competency_scores: dict[str, list[float]] = {}
    for ev in evidence:
        comp = ev.competency
        if comp not in competency_scores:
            competency_scores[comp] = []
        competency_scores[comp].append(float(ev.score))

    comp_defs = [CompetencyDef(**c) for c in template.competencies]
    scores = {}
    total_weight = 0.0
    weighted_sum = 0.0

    for cd in comp_defs:
        raw_scores = competency_scores.get(cd.id, [])
        avg = sum(raw_scores) / len(raw_scores) if raw_scores else 0.0
        normalized = (avg / cd.max_score) * 10.0
        scores[cd.id] = {
            "raw_avg": round(avg, 2),
            "normalized": round(normalized, 2),
            "weight": cd.weight,
            "weighted": round(normalized * cd.weight, 2),
            "evidence_count": len(raw_scores),
        }
        weighted_sum += normalized * cd.weight
        total_weight += cd.weight

    final_weighted = round(weighted_sum / total_weight, 2) if total_weight else 0.0

    existing_result = await db.execute(
        select(ScorecardResult).where(
            ScorecardResult.session_id == session_id,
            ScorecardResult.template_id == template_id,
        )
    )
    result = existing_result.scalar_one_or_none()
    if result:
        result.scores = scores
        result.weighted_score = final_weighted
    else:
        result = ScorecardResult(
            id=uuid.uuid4(),
            session_id=session_id,
            template_id=template_id,
            scores=scores,
            weighted_score=final_weighted,
        )
        db.add(result)

    await db.commit()
    await db.refresh(result)
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
