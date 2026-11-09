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

from app.auth.middleware import optional_auth
from app.candidates.auth import optional_candidate_auth
from app.database.session import get_session_factory
from app.models.db import CandidateProfile, InterviewSession, Organization, User
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
    current_user: Optional[User] = None,
) -> InterviewSession:
    org_access = False
    async with get_session_factory()() as db:
        result = await db.execute(
            select(InterviewSession).where(InterviewSession.id == UUID(session_id))
        )
        session = result.scalar_one_or_none()
        if session is not None and current_user is not None:
            # The recruiter reads the report of an interview run for their own organization (same rule as
            # require_org_role: the organization's owner, or a system admin).
            if current_user.is_admin:
                org_access = True
            elif session.org_id is not None:
                owned = await db.execute(
                    select(Organization.id).where(
                        Organization.id == session.org_id,
                        Organization.owner_user_id == current_user.id,
                    )
                )
                org_access = owned.scalar_one_or_none() is not None
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if org_access:
        return session
    if session.candidate_profile_id is not None:
        if not current_candidate:
            raise HTTPException(status_code=401, detail="Authentication required")
        if str(session.candidate_profile_id) != str(current_candidate.id):
            raise HTTPException(status_code=403, detail="You don't own this session")
    return session


def split_feedback_items(text: Optional[str]) -> list[str]:
    """Turn a stored strengths/weaknesses string back into its items.

    New rows hold one item per line. Older rows were joined with ", ", so they are split only on commas
    outside brackets: "Applies concrete fixes (index, cache), clear steps" stays two items, not four.
    """
    if not text:
        return []
    if "\n" in text:
        parts = text.split("\n")
    else:
        parts, depth, start = [], 0, 0
        for i, ch in enumerate(text):
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth = max(0, depth - 1)
            elif ch == "," and depth == 0:
                parts.append(text[start:i])
                start = i + 1
        parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def top_feedback_items(items: list[str], limit: int = 8) -> list[str]:
    """The points made most often across the interview, most frequent first (ties keep first-seen order).

    A 14-question interview yields dozens of near-duplicate strengths and weaknesses; ``list(set(...))`` returned all
    of them in random order. Case and trailing punctuation are ignored when counting repeats.
    """
    counts: dict[str, int] = {}
    first: dict[str, tuple[int, str]] = {}
    for index, item in enumerate(items):
        key = item.strip().rstrip(".;:").lower()
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
        first.setdefault(key, (index, item.strip()))
    ranked = sorted(counts, key=lambda k: (-counts[k], first[k][0]))
    return [first[k][1] for k in ranked[:limit]]


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

    answered_questions = len([m for m in messages if m.get("role") == "user"])
    # Organization interviews store no question total: fall back to the engine's own cap (not a made-up 10), and
    # never report fewer possible questions than were actually answered ("13 / 10", "130%").
    from app.config.interview_styles import get_style

    default_total = int(get_style("AURA").get("max_questions", 14) or 14)
    total_questions_possible = max(int(session.get("total_questions") or default_total), answered_questions, 1)

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
            all_strengths.extend(split_feedback_items(e["strengths"]))
        if e.get("weaknesses"):
            all_weaknesses.extend(split_feedback_items(e["weaknesses"]))

    return {
        "session_id": session_id,
        "org_id": session.get("org_id"),
        "it_role_id": session.get("it_role_id"),
        "job_role": session.get("job_role_snapshot"),
        "status": session.get("status"),
        "current_phase": session.get("current_phase"),
        "question_number": session.get("current_question_number"),
        "total_questions": total_questions_possible,
        "final_score": round(avg_score, 2) if avg_score else session.get("final_score"),
        "hiring_score": session.get("final_score"),
        "average_answer_score": round(avg_score, 2) if avg_score else None,
        "technical_score": round(avg_technical, 2) if avg_technical else None,
        "communication_score": round(avg_communication, 2) if avg_communication else None,
        "strengths": top_feedback_items(all_strengths),
        "weaknesses": top_feedback_items(all_weaknesses),
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
    current_user: Optional[User] = Depends(optional_auth),
):
    """
    Get comprehensive session summary.
    Returns all questions, evaluations, and metrics.
    Includes engine extras (competency coverage, hypothesis outcomes) for
    v4/v5 sessions, read from the durable ``interview_brain`` snapshot.
    """
    db_session = await _verify_session_access(session_id, current_candidate, current_user)
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
