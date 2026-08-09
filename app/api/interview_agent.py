"""
AI Interview Agent API - Session Summary Endpoint
The live engine is V5 (WebSocket-driven via /ws/interview/{session_id} ->
InterviewEngine). Only the summary endpoint remains here: it reads the durable
DB state (session/message/evaluation rows plus the V5 ``interview_brain``
snapshot) and serves the post-interview report page.
"""
import asyncio
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.candidates.auth import optional_candidate_auth
from app.database.session import get_session_factory
from app.models.db import CandidateProfile, InterviewSession
from app.exceptions import SessionNotFoundException
from app.services.repositories import (
    get_evaluation_repo,
    get_message_repo,
    get_session_repo,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Interview Agent"])


# ============================================================================
# HELPERS
# ============================================================================

async def _verify_session_access(
    session_id: str,
    current_candidate: Optional[CandidateProfile],
) -> InterviewSession:
    async with get_session_factory()() as db:
        result = await db.execute(
            select(InterviewSession).where(InterviewSession.id == UUID(session_id))
        )
        session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.candidate_profile_id is not None:
        if not current_candidate:
            raise HTTPException(status_code=401, detail="Authentication required")
        if str(session.candidate_profile_id) != str(current_candidate.id):
            raise HTTPException(status_code=403, detail="You don't own this session")
    return session


async def _get_legacy_summary(session_id: str) -> dict:
    """Build the legacy v3 summary directly from DB state.

    Formerly InterviewOrchestrator.get_session_summary — replicated here so the
    summary endpoint keeps working for v3-versioned sessions after the archive.
    """
    session_task = get_session_repo().get_session(session_id)
    messages_task = get_message_repo().get_session_messages(session_id)
    session, messages = await asyncio.gather(session_task, messages_task)

    try:
        evaluations = await get_evaluation_repo().get_evaluations_by_session(session_id)
    except Exception:
        evaluations = []

    answered_questions = len([m for m in messages if m.get("role") == "candidate"])
    total_questions_possible = int(session.get("total_questions") or 10)

    if evaluations:
        scores = [float(e.get("score", 0)) for e in evaluations]
        technical_scores = [
            float(e.get("technical_score", 0))
            for e in evaluations
            if e.get("technical_score")
        ]
        comm_scores = [
            float(e.get("communication_score", 0))
            for e in evaluations
            if e.get("communication_score")
        ]
    else:
        message_evals = await get_message_repo().get_evaluations(session_id)
        scores = [float(e.get("score", 0)) for e in message_evals]
        technical_scores = []
        comm_scores = []

    avg_score = sum(scores) / len(scores) if scores else (session.get("final_score") or 0)
    avg_technical = sum(technical_scores) / len(technical_scores) if technical_scores else None
    avg_communication = sum(comm_scores) / len(comm_scores) if comm_scores else None

    all_strengths = []
    all_weaknesses = []
    for e in evaluations:
        if e.get("strengths"):
            all_strengths.extend([s.strip() for s in e["strengths"].split(",") if s.strip()])
        if e.get("weaknesses"):
            all_weaknesses.extend([w.strip() for w in e["weaknesses"].split(",") if w.strip()])

    return {
        "session_id": session_id,
        "department_id": session.get("department_id"),
        "job_role": session.get("job_role"),
        "status": session.get("status"),
        "current_phase": session.get("current_phase"),
        "question_number": session.get("current_question_number"),
        "total_questions": total_questions_possible,
        "final_score": round(avg_score, 2) if avg_score else session.get("final_score"),
        "hiring_score": session.get("final_score"),
        "average_answer_score": round(avg_score, 2) if avg_score else None,
        "technical_score": round(avg_technical, 2) if avg_technical else None,
        "communication_score": round(avg_communication, 2) if avg_communication else None,
        "strengths": list(set(all_strengths)),
        "weaknesses": list(set(all_weaknesses)),
        "answered_ratio": (
            round(answered_questions / total_questions_possible, 2)
            if total_questions_possible > 0
            else 0
        ),
        "total_questions_answered": answered_questions,
        "messages_count": len(messages),
        "evaluations_count": len(evaluations),
        "interview_complete": session.get("status") == "completed",
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "messages": messages,
        "evaluations": evaluations,
    }


async def _get_engine_summary(session_id: str) -> dict:
    """V4/V5 extras from the durable ``interview_brain`` snapshot (DB).

    The engine snapshots the brain into ``interview_brain`` on every turn via
    ``V5BrainPersister`` (and at completion). The in-memory session store is
    NOT a reliable source after a restart or eviction, so the summary reads the
    snapshot table instead. The payload keeps the legacy ``v4_*`` key names for
    API compatibility.

    Best-effort: any failure (e.g. the table missing pre-migration) degrades to
    an empty dict, and the caller falls back to the legacy summary alone.
    """
    from app.models.db import InterviewBrain as InterviewBrainRecord

    try:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(InterviewBrainRecord).where(
                    InterviewBrainRecord.session_id == UUID(session_id)
                )
            )
            record = result.scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001 - best-effort summary extras
        logger.warning(f"V5 brain snapshot read failed (non-fatal): {exc}")
        return {}

    if not record:
        return {}

    decision = record.decision_state or {}
    rec = decision.get("hiring_recommendation", {})
    summary = record.evidence_summary or {}
    hypotheses = record.current_hypotheses or []
    metadata = record.brain_metadata or {}

    engine_data = {
        "session_id": session_id,
        "v4_verdict": rec.get("verdict", "insufficient_evidence"),
        "v4_confidence": rec.get("confidence", 0),
        "v4_composite_score": rec.get("composite_score"),
        # Canonical override: v4/v5 sessions must report the engine's single
        # composite (== persisted session.final_score), never a re-derived
        # per-turn average that disagrees with the recommendation/decision.
        "v4_evidence_count": sum(
            s.get("evidence_count", 0) for s in summary.values()
        ),
        "v4_questions_asked": metadata.get("question_number", 0),
        "v4_competency_summary": {
            comp: {
                "average_score": s.get("average_score", 0),
                "evidence_count": s.get("evidence_count", 0),
                "gap": s.get("gap", 1),
            }
            for comp, s in summary.items()
        },
        "v4_hypothesis_outcomes": {
            "confirmed": sum(1 for h in hypotheses if h.get("status") == "confirmed"),
            "refuted": sum(1 for h in hypotheses if h.get("status") == "refuted"),
            "testing": sum(1 for h in hypotheses if h.get("status") == "testing"),
            "untested": sum(1 for h in hypotheses if h.get("status") == "untested"),
        },
    }
    if rec.get("composite_score") is not None:
        engine_data["final_score"] = rec.get("composite_score")
    return engine_data


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/interviews/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    current_candidate: Optional[CandidateProfile] = Depends(optional_candidate_auth),
):
    """
    Get comprehensive session summary.
    Returns all questions, evaluations, and metrics.
    Includes engine extras (competency coverage, hypothesis outcomes) for
    v4/v5 sessions, read from the durable ``interview_brain`` snapshot.
    """
    db_session = await _verify_session_access(session_id, current_candidate)
    engine = db_session.engine_version or "v3"

    if engine in ("v4", "v5"):
        engine_data = await _get_engine_summary(session_id)
        try:
            base = await _get_legacy_summary(session_id)
        except SessionNotFoundException:
            base = None
        if base:
            return {**base, **engine_data}
        if engine_data:
            return engine_data

    try:
        result = await _get_legacy_summary(session_id)
        return result
    except SessionNotFoundException:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.exception("Failed to get session summary")
        raise HTTPException(status_code=500, detail=str(e))
