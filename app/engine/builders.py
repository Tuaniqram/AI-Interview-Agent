"""Response builders for the V5 interview engine.

Accept an ``InterviewBrain`` or a plain dict so the API shims and the
WebSocket handler can share one implementation. The underscore aliases at the
bottom keep the legacy import names working for tests (the original
``app/api/interview_v4.py`` module was deleted in the Phase 10 cleanup).
"""
from typing import Any, Union
from collections import Counter

from app.config import settings
from app.core.interview_brain import InterviewBrain
from app.core.interview_state import brain_to_dict

StateLike = Union[InterviewBrain, dict]


def _as_dict(state: StateLike) -> dict:
    return brain_to_dict(state) if isinstance(state, InterviewBrain) else state


def compose_conversation_turn(state: StateLike) -> str:
    """Compose the spoken message: acknowledgement + bridge + question."""
    from app.intelligence._helpers import unwrap_turn_json

    s = _as_dict(state)
    turn = s.get("conversation_turn") or {}
    if isinstance(turn, dict) and turn.get("question"):
        # last line of defence: never show a JSON-encoded turn to the candidate
        turn = unwrap_turn_json(turn["question"]) or turn
        parts = [
            p
            for p in (turn.get("acknowledgement", ""), turn.get("bridge", ""), turn["question"])
            if p
        ]
        return "\n\n".join(parts)
    current = s.get("current_question", "")
    unwrapped = unwrap_turn_json(current)
    if unwrapped:
        return "\n\n".join(
            p for p in (unwrapped["acknowledgement"], unwrapped["bridge"], unwrapped["question"]) if p
        )
    return current


def _integrity_policy(s: dict) -> dict:
    """Anti-cheat policy surfaced on the session-start payload (contract §4.3).

    Always present so a (possibly rebuilt) frontend can render the rules gate
    consistently: when the guard is off, ``enabled: false`` and no max flags —
    the rules screen shows generic conduct rules only.
    """
    from app.services.anti_cheat import flagged_count, max_flags

    return {
        "enabled": bool(settings.ANTI_CHEAT_GUARD_ENABLED),
        "max_flags": max_flags() if settings.ANTI_CHEAT_GUARD_ENABLED else 0,
        "flagged_count": flagged_count(s.get("integrity_signals")),
        "answer_time_limit_s": (
            int(settings.ANTI_CHEAT_ANSWER_TIME_LIMIT_S or 0)
            if settings.ANTI_CHEAT_GUARD_ENABLED
            else 0
        ),
    }


def _live_integrity(s: dict) -> dict | None:
    """Live flag gauge data for the answer response (contract §4.4).

    Present only when the guard is enabled and at least one signal exists —
    otherwise the frontend renders no gauge.
    """
    if not settings.ANTI_CHEAT_GUARD_ENABLED:
        return None
    from app.services.anti_cheat import flagged_count, max_flags

    signals = s.get("integrity_signals") or []
    if not signals:
        return None
    return {
        "flagged_count": flagged_count(signals),
        "max_flags": max_flags(),
        "score": s.get("integrity_score"),
    }


def build_start_response(session_id: str, state: StateLike) -> dict:
    """Build the ``{type: question}`` payload for session start / resume."""
    s = _as_dict(state)
    target = s.get("hypothesis_target") or {}
    question = s.get("current_question", "")
    next_comp = s.get("next_competency") or {}
    comp_id = next_comp.get("id", "") if isinstance(next_comp, dict) else ""

    return {
        "session_id": session_id,
        "status": "in_progress",
        "job_role": s.get("job_role", ""),
        "department_id": s.get("department_id"),
        "org_id": s.get("org_id"),  # set for real (organization) interviews, absent for practice
        "conversation_turn": compose_conversation_turn(s),
        "question": {
            "text": question,
            "number": s.get("question_number", 1),
            "target_competency": target.get("competency", comp_id),
            "target_hypothesis": target.get("statement", ""),
        },
        "hypothesis_target": {
            "statement": target.get("statement", ""),
            "confidence": target.get("confidence", 0.0),
            "status": target.get("status", "untested"),
        }
        if target
        else None,
        "persona": s.get("persona", "friendly"),
        "difficulty": s.get("difficulty_level", 1),
        "competencies": {
            "planned": len(s.get("required_competencies", [])),
            "next": comp_id,
        },
        "integrity_policy": _integrity_policy(s),
    }


def refresh_sufficiency_and_recommendation(state: StateLike) -> tuple[dict, dict]:
    """Recompute ``evidence_sufficiency`` + ``hiring_recommendation`` from the
    *current* hypothesis state in one pass.

    The reflection computes both before the turn's hypothesis update, so
    payloads/snapshots built later showed stale counts that disagreed with
    ``hypothesis_progress`` — and refreshing only the recommendation left the
    persisted pair disagreeing (``hiring_recommendation.unanswered_hypotheses``
    vs ``evidence_sufficiency.unanswered_hypotheses``). Recomputing both from
    the same snapshot keeps them consistent; falls back to the stored values
    if evaluation fails.
    """
    s = _as_dict(state)
    try:
        from app.agents.planning.difficulty_engine import max_difficulty_reached
        from app.agents.reasoning.contradiction_engine import (
            competency_weights,
            evaluate_sufficiency,
        )

        return evaluate_sufficiency(
            competency_summary=s.get("competency_summary", {}),
            required_competencies=s.get("required_competencies", []) or [],
            contradictions=s.get("contradictions", []),
            hypotheses=s.get("hypotheses", []),
            question_number=int(s.get("question_number", 0) or 0),
            comp_weights=competency_weights(s),
            difficulty_reached=max_difficulty_reached(s),
            unanswered_hypotheses=sum(
                1
                for h in (s.get("hypotheses") or [])
                if h.get("status") in ("untested", "testing")
            ),
        )
    except Exception:
        return s.get("evidence_sufficiency", {}), s.get("hiring_recommendation", {})


def refresh_hiring_recommendation(state: StateLike) -> dict:
    """Recompute the hiring recommendation from the *current* hypothesis state.

    Convenience wrapper over :func:`refresh_sufficiency_and_recommendation` for
    payload builders that only need the recommendation (answer responses).
    """
    _, recommendation = refresh_sufficiency_and_recommendation(state)
    return recommendation or {}


def build_answer_response(session_id: str, state: StateLike) -> dict:
    """Build the ``{type: evaluation}`` payload after an answered turn."""
    s = _as_dict(state)
    evaluation = s.get("unified_evaluation", {})
    target = s.get("hypothesis_target") or {}
    next_comp = s.get("next_competency") or {}

    scored = {}
    for dim, data in evaluation.items():
        if isinstance(data, dict) and data.get("score") is not None:
            scored[dim] = {
                "score": data["score"],
                "evidence": (data.get("evidence", "") or "")[:200],
                "strengths": data.get("strengths", []),
                "weaknesses": data.get("weaknesses", []),
            }

    cs = s.get("competency_summary", {})
    competency_progress = {}
    for comp_id, summary in cs.items():
        competency_progress[comp_id] = {
            "evidence_count": summary.get("evidence_count", 0),
            "average_score": summary.get("average_score", 0.0),
            "gap": summary.get("gap", 1.0),
        }

    hyp_statuses = {}
    for h in s.get("hypotheses") or []:
        st = h.get("status", "untested")
        hyp_statuses[st] = hyp_statuses.get(st, 0) + 1

    next_question = s.get("current_question", "")
    next_comp_id = next_comp.get("id", "") if isinstance(next_comp, dict) else ""

    return {
        "session_id": session_id,
        "status": "in_progress",
        "job_role": s.get("job_role", ""),
        "department_id": s.get("department_id"),
        "org_id": s.get("org_id"),  # set for real (organization) interviews, absent for practice
        "conversation_turn": compose_conversation_turn(s),
        "evaluation": {
            "scores": scored,
            "composite": s.get("evaluation_score"),
            # False when the answer could not be evaluated: the UI must not show that as 0.0.
            "scored": not s.get("evaluation_failed", False),
        },
        "next_question": {
            "text": next_question,
            "number": s.get("question_number", 0),
            "target_competency": target.get("competency", next_comp_id),
        },
        "evidence": {
            "total": len(s.get("evidence_store", [])),
            "competencies_covered": len(competency_progress),
            "competency_progress": competency_progress,
        },
        "hypothesis_progress": {
            "total": len(s.get("hypotheses", [])),
            "statuses": hyp_statuses,
        },
        "contradictions": len(s.get("contradictions", [])),
        "hiring_recommendation": refresh_hiring_recommendation(s),
        "integrity": _live_integrity(s),
        "brain": {
            "question_strategy": s.get("question_strategy") or {},
            "uncertainty": s.get("uncertainty_map") or {},
            "contradiction_state": s.get("contradiction_state") or {},
            "calibration_state": s.get("calibration_state") or {},
            "difficulty_state": s.get("difficulty_state") or {},
            "candidate_memory": s.get("candidate_memory") or {},
            "brain_utilization": s.get("brain_utilization") or {},
            "evidence_cursor": s.get("evidence_cursor") or {},
        },
    }


def build_state_response(session_id: str, state: StateLike) -> dict:
    """Build the ``{type: status_snapshot}`` payload for get_status."""
    s = _as_dict(state)

    return {
        "session_id": session_id,
        "question_number": s.get("question_number", 0),
        "persona": s.get("persona", ""),
        "job_role": s.get("job_role", ""),
        "department_id": s.get("department_id"),
        "org_id": s.get("org_id"),  # set for real (organization) interviews, absent for practice
        "conversation_turn": compose_conversation_turn(s),
        "current_question": s.get("current_question", ""),
        "interview_complete": bool(s.get("reflection_action") == "finish"),
        "difficulty": s.get("difficulty_level", 1),
        "evidence_count": len(s.get("evidence_store", [])),
        "competency_coverage": {
            comp: s_.get("evidence_count", 0)
            for comp, s_ in (s.get("competency_summary") or {}).items()
        },
        "hypothesis_summary": {
            "total": len(s.get("hypotheses", [])),
            "confirmed": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "confirmed"),
            "refuted": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "refuted"),
            "testing": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "testing"),
        },
        "contradictions": len(s.get("contradictions", [])),
        "hiring_recommendation": s.get("hiring_recommendation", {}),
        "evaluation_score": s.get("evaluation_score"),
    }


def _evidence_reading_summary(reading: dict | None) -> dict | None:
    """Compact evidence_reading summary for the report payload (None when absent)."""
    if not reading:
        return None
    per = reading.get("per_answer") or {}
    counts = Counter(
        entry.get("claim_classification", "mentioned")
        for entry in per.values()
        if isinstance(entry, dict)
    )
    return {
        "answers_read": len(per),
        "claim_classification": {
            name: counts.get(name, 0) for name in ("mentioned", "demonstrated", "proven")
        },
        "off_rubric_red_flags": reading.get("off_rubric", {}).get("red_flags") or [],
        "hidden_strengths": reading.get("off_rubric", {}).get("hidden_strengths") or [],
        "semantic_risks": reading.get("semantic_risks") or [],
    }


def _integrity_summary(s: dict) -> dict | None:
    """Anti-cheat aggregate for the report payload (contract §4.2).

    ``None`` when the guard recorded no signals (disabled or nothing flagged —
    absent in the report is semantically "no signals recorded"). Only includes
    stored per-answer signals; keys are frozen by the contract.
    """
    signals = s.get("integrity_signals") or []
    if not signals:
        return None
    compact = []
    for sig in signals:
        compact.append(
            {
                "question_number": sig.get("question_number"),
                "score": sig.get("score"),
                "latency_secs": sig.get("latency_secs"),
                "paste_hint": bool(sig.get("paste_hint")),
                "focus_losses": int(sig.get("focus_losses") or 0),
                "duplicate_ratio": sig.get("duplicate_ratio"),
                "pointer_leaves": int(sig.get("pointer_leaves") or 0),
                "heartbeat_gaps": int(sig.get("heartbeat_gaps") or 0),
                "cadence_score": sig.get("cadence_score"),
                "llm_ai_score": sig.get("llm_ai_score"),
                "reasons": sig.get("reasons") or [],
            }
        )
    return {
        "score": s.get("integrity_score", max((x.get("score", 0) for x in compact), default=0)),
        "flagged": bool(
            (s.get("integrity_score", 0) or 0)
            >= int(settings.ANTI_CHEAT_FLAG_THRESHOLD or 70)
        ),
        "signals": compact,
    }


def build_report_response(state: StateLike) -> dict:
    """Build the final ``{type: report}`` payload on interview completion."""
    s = _as_dict(state)
    rec = s.get("hiring_recommendation", {})
    hd = s.get("hiring_decision") or {}
    cs = s.get("competency_summary", {})
    graph = s.get("evidence_graph") or {}
    profile = s.get("difficulty_profile")

    # V5: ONE source of truth for the verdict — the deterministic 7-point
    # decision (difficulty credit + coverage caps). The recommendation and any
    # LLM draft explain it, they never replace it, so the report can never
    # show "strong_hire" next to "lean_hire".
    final_verdict = hd.get("decision") or rec.get("verdict", "insufficient_evidence")

    # D3: separate the metrics a reader can see — the per-answer average is
    # NOT the holistic fit score. ``composite_score`` stays the hiring
    # anchor, but the report now exposes both plus the question progress so
    # "73% coverage" can never be confused with "6 of 10 questions asked".
    from app.agents.evaluation.synthesis import _score_timeline
    from app.agents.planning.difficulty_engine import max_difficulty_reached

    timeline = _score_timeline(s)
    avg_answer = (
        round(sum(t["score"] for t in timeline) / len(timeline), 2)
        if timeline
        else None
    )
    answered = int(s.get("question_number", 0) or 0)
    planned = int(s.get("total_questions", 0) or 0)

    report = {
        "status": "completed",
        "verdict": final_verdict,
        "hiring_recommendation": {
            "verdict": final_verdict,
            "confidence": rec.get("confidence", 0.0),
            "composite_score": rec.get("composite_score"),
            "decision_score": hd.get("decision_score"),
            "coverage_ratio": rec.get("coverage_ratio"),
            "composite_score_note": (
                "holistic fit score (competency average 50%, hypothesis "
                "confidence 30%, coverage 20%) — not the per-answer average; "
                "the final verdict is the deterministic hiring_decision"
            ),
        },
        "interview_performance": {
            "average_answer_score": avg_answer,
            "score_timeline": timeline,
        },
        "question_progress": {
            "answered": answered,
            "planned": planned,
            "ratio": round(answered / planned, 2) if planned > 0 else 0,
        },
        "coverage": {
            "competency_coverage_ratio": rec.get("coverage_ratio"),
            "note": (
                "weighted fraction of required competencies with minimum "
                "evidence and no gap — not the question-answered ratio"
            ),
        },
        "difficulty_reached": (profile or {}).get("level", max_difficulty_reached(s)),
        "competency_summary": {
            comp: {
                "average_score": s_.get("average_score", 0.0),
                "evidence_count": s_.get("evidence_count", 0),
                "gap": s_.get("gap", 1.0),
            }
            for comp, s_ in cs.items()
        },
        "evidence_collected": len(s.get("evidence_store", [])),
        "questions_asked": answered,
        "hypothesis_outcomes": {
            "confirmed": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "confirmed"),
            "refuted": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "refuted"),
            "testing": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "testing"),
            "untested": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "untested"),
        },
        "evidence_graph": {
            "competency_nodes": len((graph.get("nodes") or {})),
            "evidence_edges": len((graph.get("edges") or {})),
        },
        "difficulty_profile": profile,
        "hiring_decision": s.get("hiring_decision", {}),
        "aura_brain": s.get("aura_brain") or {},
        "evidence_reading": _evidence_reading_summary(s.get("evidence_reading")),
    }
    integrity = _integrity_summary(s)
    if integrity is not None:
        report["integrity"] = integrity
    if s.get("integrity_terminated"):
        report["integrity_terminated"] = True
        report["integrity_termination_reason"] = (
            "The candidate accumulated the maximum allowed integrity flags. "
            "The interview was terminated before completion."
        )
    return report


# Backward-compat aliases for any code that imported the underscore names.
_build_start_response = build_start_response
_build_answer_response = build_answer_response
_build_state_response = build_state_response
_build_report_response = build_report_response
_compose_conversation_turn = compose_conversation_turn
