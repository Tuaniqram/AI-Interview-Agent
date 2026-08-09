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
from app.intelligence.persist import persist_intelligence_bundle
from app.models.db import CandidateProfile, EvidenceGraph, InterviewBrain, InterviewTimeline

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
    candidate_profile = req.candidate_profile
    resume_text = req.resume_text

    if req.candidate_id and candidate_profile is None and not resume_text:
        loaded_profile, loaded_text = await _load_candidate_from_db(
            db, req.candidate_id
        )
        candidate_profile = loaded_profile
        resume_text = resume_text or loaded_text

    bundle = await build_interview_intelligence(
        job_role=req.job_role,
        department_id=req.department_id,
        candidate_id=req.candidate_id,
        candidate_profile=candidate_profile,
        resume_text=resume_text,
        required_competencies=req.required_competencies,
        scorecard_competencies=req.scorecard_competencies,
        use_rag=req.use_rag,
        use_llm=req.use_llm,
    )

    session_id = UUID(req.session_id) if req.session_id else None
    persisted = None
    if session_id:
        persisted = await persist_intelligence_bundle(
            session_id, req.department_id, req.job_role, bundle, db=db
        )

    return {
        "intelligence": bundle,
        "persisted": persisted,
        "session_id": str(session_id) if session_id else None,
    }


async def _load_candidate_from_db(
    db: AsyncSession, candidate_id: str
) -> tuple[dict | None, str | None]:
    """Resolve the candidate profile + resume-ish text from the DB.

    Used when a build request only carries ``candidate_id`` so the candidate
    brain is not seeded from an empty profile.
    """
    try:
        result = await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.id == UUID(candidate_id)
            )
        )
    except ValueError:
        return None, None
    profile = result.scalar_one_or_none()
    if profile is None:
        return None, None

    data = dict(profile.profile_data or {})
    data.setdefault("full_name", profile.name)
    data.setdefault("headline", "")
    data.setdefault("strengths", [])
    data.setdefault("weaknesses", [])

    parts = [profile.name or "", profile.skills or ""]
    for value in data.values():
        if isinstance(value, str) and value.strip():
            parts.append(value)
        elif isinstance(value, list):
            parts.append(", ".join(str(v) for v in value if v))
    resume_text = "\n".join(p for p in parts if p.strip()) or None
    return data, resume_text


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

    brain_metadata = (brain_row.brain_metadata or {}) if brain_row else {}
    aura_brain = brain_metadata.get("aura_brain") or {}
    interview_brain = {
        "version": brain_row.version if brain_row else None,
        "current_hypotheses": brain_row.current_hypotheses if brain_row else [],
        "evidence_summary": brain_row.evidence_summary if brain_row else {},
        "competency_scores": brain_row.competency_scores if brain_row else {},
        "difficulty_profile": brain_row.difficulty_profile if brain_row else None,
        "decision_state": brain_row.decision_state if brain_row else None,
    }
    # Additive-only: the 13-layer aura brain surfaces under `brain_layers`.
    # The layers share entity ids (evidence/hypothesis/competency) and link
    # through the evidence_graph edges + the decision pipeline below.
    role_brain = aura_brain.get("role_brain") or {}
    if role_brain.get("role"):
        interview_brain["role"] = role_brain["role"]
    brain_layers = dict(aura_brain)
    # `evidence_summary` lives on the V5 column, not inside aura_brain.
    brain_layers.setdefault(
        "evidence_summary", brain_row.evidence_summary if brain_row else {}
    )
    if brain_layers:
        interview_brain["brain_layers"] = brain_layers

    return {
        "session_id": str(session_id),
        "interview_brain": interview_brain,
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
