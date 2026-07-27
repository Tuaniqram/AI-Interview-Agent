from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory
from app.models.db import (
    EvidenceStore,
    InterviewSession,
    ScorecardResult,
    ScorecardTemplate,
)
from app.scorecards.schemas import CompetencyDef, ScorecardResultResponse


async def calculate_scorecard_for_session(
    db: AsyncSession,
    session_id: UUID,
    template_id: UUID,
) -> Optional[ScorecardResultResponse]:
    template_result = await db.execute(
        select(ScorecardTemplate).where(ScorecardTemplate.id == template_id)
    )
    template = template_result.scalar_one_or_none()
    if not template:
        return None

    ev_result = await db.execute(
        select(EvidenceStore).where(EvidenceStore.session_id == session_id)
    )
    evidence = ev_result.scalars().all()

    comp_defs = [CompetencyDef(**c) for c in template.competencies]
    competency_scores: dict[str, list[float]] = {}
    for ev in evidence:
        comp = ev.competency
        if comp not in competency_scores:
            competency_scores[comp] = []
        competency_scores[comp].append(float(ev.score))

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
    return ScorecardResultResponse(
        id=result.id,
        session_id=result.session_id,
        template_id=result.template_id,
        scores=result.scores,
        weighted_score=result.weighted_score,
        created_at=result.created_at,
    )


async def auto_calculate_on_complete(
    session_id: str,
    scorecard_template_id: str,
) -> None:
    from uuid import UUID as UUIDCast
    try:
        async with get_session_factory()() as db:
            await calculate_scorecard_for_session(
                db=db,
                session_id=UUIDCast(session_id),
                template_id=UUIDCast(scorecard_template_id),
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"Auto-scorecard calculation failed for session {session_id}: {e}"
        )
