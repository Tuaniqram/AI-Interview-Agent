"""DB persistence helpers for the V5 interview engine.

All writes are best-effort by design — persistence must never break an
interview. Extracted from the original ``InterviewEngine`` so the coordinator
stays a thin routing shell.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.interview_brain import InterviewBrain

logger = logging.getLogger(__name__)

_NON_TECHNICAL_DIMS = {
    "communication",
    "reasoning",
    "behavioral",
    "confidence",
    "completeness",
}


def summarize_hypotheses(hypotheses: list) -> list[dict]:
    """Compact hypothesis summaries for the event log (before/after diffs)."""
    return [
        {
            "id": h.get("id", ""),
            "competency": h.get("competency", ""),
            "direction": h.get("direction", ""),
            "confidence": h.get("confidence"),
            "probability": h.get("probability", h.get("confidence")),
            "status": h.get("status", "untested"),
            "supporting_count": len(h.get("supporting_evidence", [])),
            "contradicting_count": len(h.get("contradicting_evidence", [])),
        }
        for h in hypotheses
    ]


def extract_answer_turn(brain: InterviewBrain) -> Optional[dict]:
    """Pull the latest (question, answer) pair and its evaluation from a brain."""
    conv = brain.conversation_history or []
    if len(conv) < 2:
        return None
    q_entry, a_entry = conv[-2], conv[-1]
    if q_entry.get("role") != "assistant" or a_entry.get("role") != "user":
        return None
    question_text = (q_entry.get("content") or "").strip()
    answer_text = (a_entry.get("content") or "").strip()
    if not question_text or not answer_text:
        return None
    return {
        "question": question_text,
        "answer": answer_text,
        "question_number": brain.question_number,
        "phase": brain.current_phase or "technical",
        "composite": brain.evaluation_score or 0.0,
        "evaluation": brain.unified_evaluation or {},
    }


async def persist_evidence(session_id: str, state: dict) -> None:
    """Best-effort evidence rows to the DB.

    Flushes every answer's freshly-extracted evidence (evidence ids are unique
    per turn, so rows never collide). Failures are non-fatal by design.
    """
    try:
        from app.repositories.evidence_repository import EvidenceRepository

        if not session_id:
            return
        extracted = state.get("extracted_evidence") or []
        if not extracted:
            return

        repo = EvidenceRepository()
        hypotheses = state.get("hypotheses") or []
        for ev in extracted:
            evidence_metadata = {
                key: ev[key]
                for key in ("strength", "impact", "ownership", "complexity", "contradiction")
                if ev.get(key) is not None
            }
            # Attach the evidence to its best-matching (same-competency)
            # hypothesis so the DB rows stop pointing at ghost ids.
            best_hyp = None
            best_hyp_relevance = 0.0
            try:
                from app.agents.reasoning.hypothesis_engine import compute_relevance
                from app.agents.reasoning.hypothesis_engine import RELEVANCE_THRESHOLD

                for hyp in hypotheses:
                    rel = compute_relevance(hyp, ev)
                    if rel > best_hyp_relevance:
                        best_hyp_relevance = rel
                        best_hyp = hyp
            except Exception:  # noqa: BLE001
                best_hyp = None
                best_hyp_relevance = 0.0
            hypothesis_id = (
                best_hyp["id"] if best_hyp and best_hyp_relevance >= RELEVANCE_THRESHOLD else None
            )
            await repo.create_evidence(
                session_id=session_id,
                competency=ev["competency"],
                dimension=ev["dimension"],
                score=ev["score"],
                evidence_text=ev["evidence_text"],
                source_question=ev["source_question"],
                question_number=ev["question_number"],
                confidence=ev["confidence"],
                hypothesis_id=hypothesis_id,
                hypothesis_relevance=round(best_hyp_relevance, 4) if hypothesis_id else None,
                evidence_metadata=evidence_metadata or None,
                evidence_id=ev.get("id"),
            )
    except Exception as exc:  # noqa: BLE001 - best-effort by design
        logger.warning(f"Failed to save evidence (non-fatal): {exc}")


async def persist_answer_turn(session_id: str, brain: InterviewBrain) -> None:
    """Persist the latest evaluated Q/A turn to the DB (best-effort)."""
    try:
        turn = extract_answer_turn(brain)
        if not turn:
            return
        answered = set(brain.answered_question_numbers or [])
        qnum = turn["question_number"]
        if qnum in answered:
            return
        brain.answered_question_numbers = sorted(answered | {qnum})

        technical_score = None
        communication_score = None
        strengths: list[str] = []
        weaknesses: list[str] = []
        for dim, data in (turn["evaluation"] or {}).items():
            if not isinstance(data, dict):
                continue
            if dim == "communication":
                communication_score = data.get("score")
            elif dim not in _NON_TECHNICAL_DIMS:
                technical_score = (
                    technical_score
                    if technical_score is not None
                    else data.get("score")
                )
            for item in data.get("strengths") or []:
                if isinstance(item, str) and item.strip():
                    strengths.append(item.strip())
            for item in data.get("weaknesses") or []:
                if isinstance(item, str) and item.strip():
                    weaknesses.append(item.strip())

        from app.services.repositories import (
            get_evaluation_repo,
            get_message_repo,
        )

        message_repo = get_message_repo()
        evaluation_repo = get_evaluation_repo()
        question_msg = await message_repo.create_question(
            session_id=session_id,
            question_text=turn["question"],
            question_number=qnum,
            phase=turn["phase"],
        )
        answer_msg = await message_repo.create_candidate_answer(
            session_id=session_id,
            role="candidate",
            candidate_answer=turn["answer"],
            question_number=qnum,
            phase=turn["phase"],
            score=turn["composite"],
        )
        await evaluation_repo.create_evaluation(
            session_id=session_id,
            message_id=answer_msg["id"],
            technical_score=(
                technical_score if technical_score is not None else turn["composite"]
            ),
            communication_score=(
                communication_score
                if communication_score is not None
                else turn["composite"]
            ),
            strengths=", ".join(strengths) if strengths else None,
            weaknesses=", ".join(weaknesses) if weaknesses else None,
            feedback=None,
            overall_score=turn["composite"],
        )
        logger.info(
            f"Persisted v5 turn: session={session_id[:12]}..., q#{qnum}, score={turn['composite']}"
        )
    except Exception as exc:  # noqa: BLE001 - best-effort by design
        logger.warning(f"Failed to persist v5 turn (non-fatal): {exc}")


async def persist_v5_snapshot(
    session_id: str, brain: InterviewBrain, persister, finalize: bool = False
) -> None:
    """Persist the V5 InterviewBrain/evidence-graph/timeline snapshot.

    Opt-in: only runs when the engine was constructed with a ``v5_persister``
    exposing ``save_snapshot(brain)``; failures are non-fatal by design. Also
    persists the relational reasoning tables when the persister exposes
    ``save_relational(brain, finalize=...)``.
    """
    if persister is None:
        return
    try:
        await persister.save_snapshot(brain)
        if hasattr(persister, "save_relational"):
            await persister.save_relational(brain, finalize=finalize)
    except Exception as exc:  # noqa: BLE001 - best-effort by design
        logger.warning(f"Failed to persist v5 snapshot (non-fatal): {exc}")


async def persist_completion(session_id: str, brain: InterviewBrain) -> None:
    """Persist session completion (status, final score) to the DB."""
    try:
        from app.services.repositories import get_session_repo

        rec = brain.hiring_recommendation or {}
        final_score = rec.get("composite_score")
        if final_score is None:
            final_score = brain.evaluation_score or 0.0
        final_score = round(float(final_score), 2)

        verdict = rec.get("verdict", "insufficient_evidence")
        confidence = rec.get("confidence", 0.0)
        questions_asked = brain.question_number
        evidence_count = len(brain.evidence_store or [])
        final_feedback = (
            f"Verdict: {verdict} (confidence {confidence:.2f}). "
            f"Questions asked: {questions_asked}. Evidence collected: {evidence_count}."
        )
        await get_session_repo().complete_session(
            session_id,
            final_score,
            final_feedback,
            ended_at=datetime.now(timezone.utc),
            engine_version="v5",
        )
        # The phase was stuck at "intro" for the session's whole life — close it
        # out so summaries stop reporting an intro phase on a finished interview.
        await get_session_repo().update_phase(session_id, "summary")
        logger.info(
            f"Persisted v5 completion: session={session_id[:12]}..., score={final_score}"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to persist v5 completion (non-fatal): {exc}")
