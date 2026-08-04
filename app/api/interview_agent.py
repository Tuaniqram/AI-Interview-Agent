"""
AI Interview Agent API - Session Summary Endpoint
The live engine is v4 (WebSocket-driven via /ws/interview/{session_id}).
Only the summary endpoint remains here; the v3 legacy engine (orchestrator +
LangGraph workflows) has been archived to v3/.
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
from app.services.v4_session_store import get_v4_session_store
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
    total_questions_possible = session.get("total_questions", 10)

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


async def _get_v4_summary(session_id: str) -> dict:
    store = get_v4_session_store()
    try:
        state = store.get_or_raise(session_id)
        rec = state.get("hiring_recommendation", {})
        return {
            "session_id": session_id,
            "status": "completed",
            "v4_verdict": rec.get("verdict", "insufficient_evidence"),
            "v4_confidence": rec.get("confidence", 0),
            "v4_composite_score": rec.get("composite_score"),
            "v4_evidence_count": len(state.get("evidence_store", [])),
            "v4_questions_asked": state.get("question_number", 0),
            "v4_competency_summary": {
                comp: {
                    "average_score": s.get("average_score", 0),
                    "evidence_count": s.get("evidence_count", 0),
                    "gap": s.get("gap", 1),
                }
                for comp, s in (state.get("competency_summary") or {}).items()
            },
            "v4_hypothesis_outcomes": {
                "confirmed": sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "confirmed"),
                "refuted": sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "refuted"),
                "untested": sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "untested"),
            },
        }
    except SessionNotFoundException:
        return {}


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
    Includes v4-specific data (competency coverage, hypothesis outcomes) for v4 sessions.
    """
    db_session = await _verify_session_access(session_id, current_candidate)
    engine = db_session.engine_version or "v3"

    if engine == "v4":
        v4_data = await _get_v4_summary(session_id)
        try:
            base = await _get_legacy_summary(session_id)
        except SessionNotFoundException:
            base = None
        if base:
            extras = {k: v for k, v in v4_data.items() if k not in base}
            return {**base, **extras}
        if v4_data:
            return v4_data

    try:
        result = await _get_legacy_summary(session_id)
        return result
    except SessionNotFoundException:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.exception("Failed to get session summary")
        raise HTTPException(status_code=500, detail=str(e))
