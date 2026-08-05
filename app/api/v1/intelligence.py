"""V5 Intelligence API — build and inspect the interview intelligence bundle.

Endpoints:
- ``POST /intelligence/build``      one-shot company+candidate intelligence bundle
- ``GET  /intelligence/brain/{id}`` InterviewBrain + evidence graph + timeline

All persistence is best-effort: the bundle is always returned even when the
database is unreachable.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.deps import get_db
from app.intelligence import build_interview_intelligence
from app.models.db import (
    CompanyBrain,
    EvidenceGraph,
    InterviewBlueprint,
    InterviewBrain,
    InterviewTimeline,
    Scorecard,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


class IntelligenceBuildRequest(BaseModel):
    job_role: str = Field(..., min_length=1)
    department_id: int | None = None
    candidate_id: str = ""
    candidate_profile: dict | None = None
    resume_text: str | None = None
    required_competencies: list[str] | None = None
    scorecard_competencies: list | None = None
    use_rag: bool = True
    use_llm: bool = True
    session_id: str | None = None


@router.post("/build")
async def build_intelligence(
    req: IntelligenceBuildRequest,
    db: AsyncSession = Depends(get_db),
):
    """Build the 6-key V5 intelligence bundle.

    Pass ``session_id`` to best-effort persist artifacts into the V5 tables
    (company_brains, interview_blueprints, scorecards, candidate_brains,
    candidate_evidence_requirements).
    """
    bundle = await build_interview_intelligence(
        job_role=req.job_role,
        department_id=req.department_id,
        candidate_id=req.candidate_id,
        candidate_profile=req.candidate_profile,
        resume_text=req.resume_text,
        required_competencies=req.required_competencies,
        scorecard_competencies=req.scorecard_competencies,
        use_rag=req.use_rag,
        use_llm=req.use_llm,
    )

    session_id = UUID(req.session_id) if req.session_id else None
    persisted = None
    if session_id:
        persisted = await _persist_bundle(db, session_id, req.department_id, req.job_role, bundle)

    return {
        "intelligence": bundle,
        "persisted": persisted,
        "session_id": str(session_id) if session_id else None,
    }


async def _persist_bundle(
    db: AsyncSession,
    session_id: UUID,
    department_id: int | None,
    job_role: str,
    bundle: dict,
) -> dict:
    """Best-effort persist of the bundle into the V5 tables."""
    saved = {"company_brain": False, "scorecard": False, "blueprint": False,
             "candidate_brain": False, "evidence_requirements": False}
    try:
        cb = bundle.get("company_brain") or {}
        db.add(CompanyBrain(
            session_id=session_id,
            department_id=department_id,
            company_name=cb.get("company_name") or job_role or "Unknown Company",
            industry=cb.get("industry"),
            company_vision=cb.get("company_vision") or cb.get("mission"),
            values=cb.get("values") or [],
            technical_stack=cb.get("technical_stack") or cb.get("tech_stack") or [],
            culture=cb.get("culture") or [],
            success_signals=cb.get("success_signals") or [],
            red_flags=cb.get("red_flags") or [],
            source_documents=cb.get("source_documents") or [],
        ))
        saved["company_brain"] = True

        blueprint = bundle.get("interview_blueprint") or {}
        db.add(InterviewBlueprint(
            session_id=session_id,
            department_id=department_id,
            role=job_role,
            objectives=blueprint.get("objectives") or [],
            phases=blueprint.get("phases") or [],
            hypothesis_template=blueprint.get("hypothesis_template") or [],
            evidence_requirements=blueprint.get("evidence_requirements") or [],
        ))
        saved["blueprint"] = True

        if blueprint.get("scorecard_competencies"):
            db.add(Scorecard(
                session_id=session_id,
                department_id=department_id,
                role=job_role,
                competencies=blueprint["scorecard_competencies"],
                required_level=blueprint.get("required_level"),
            ))
            saved["scorecard"] = True

        cand = bundle.get("candidate_brain") or {}
        from app.models.db import CandidateBrain
        db.add(CandidateBrain(
            session_id=session_id,
            candidate_id=UUID(bundle.get("candidate_id") or "") if bundle.get("candidate_id") else None,
            full_name=(cand.get("full_name") or cand.get("name") or "Unknown Candidate"),
            resume_summary=cand.get("resume_summary"),
            skills=cand.get("skills") or [],
            strengths=cand.get("strengths") or [],
            weaknesses=cand.get("weaknesses") or [],
            work_history=cand.get("work_history") or [],
            inferred_seniority=cand.get("inferred_seniority"),
            persona=cand.get("persona") or {},
        ))
        saved["candidate_brain"] = True

        requirements = bundle.get("evidence_requirements") or []
        from app.models.db import CandidateEvidenceRequirement
        for req in requirements:
            db.add(CandidateEvidenceRequirement(
                session_id=session_id,
                competency=req.get("competency") or "unknown",
                dimension=req.get("dimension") or "technical",
                required_probes=req.get("required_probes") or [],
                evidence_level=req.get("evidence_level") or "behavioral",
            ))
        saved["evidence_requirements"] = bool(requirements)

        await db.commit()
    except Exception as e:
        logger.warning(f"V5 intelligence persistence failed (best-effort): {e}")
        await db.rollback()
    return saved


@router.get("/brain/{session_id}")
async def get_brain(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return the V5 InterviewBrain snapshot + evidence graph + timeline."""
    brain_row = (
        await db.execute(
            select(InterviewBrain).where(InterviewBrain.session_id == session_id)
        )
    ).scalar_one_or_none()
    graph_row = (
        await db.execute(
            select(EvidenceGraph).where(EvidenceGraph.session_id == session_id)
        )
    ).scalar_one_or_none()
    timeline = (
        await db.execute(
            select(InterviewTimeline)
            .where(InterviewTimeline.session_id == session_id)
            .order_by(InterviewTimeline.created_at)
        )
    ).scalars().all()

    return {
        "session_id": str(session_id),
        "interview_brain": {
            "version": brain_row.version if brain_row else None,
            "current_hypotheses": brain_row.current_hypotheses if brain_row else [],
            "evidence_summary": brain_row.evidence_summary if brain_row else {},
            "competency_scores": brain_row.competency_scores if brain_row else {},
            "difficulty_profile": brain_row.difficulty_profile if brain_row else None,
            "decision_state": brain_row.decision_state if brain_row else None,
        },
        "evidence_graph": {
            "nodes": graph_row.nodes if graph_row else {},
            "edges": graph_row.edges if graph_row else {},
        },
        "timeline": [
            {
                "id": str(t.id),
                "event_type": t.event_type,
                "question_number": t.question_number,
                "event_data": t.event_data or {},
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in timeline
        ],
    }
