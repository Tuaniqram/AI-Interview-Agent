"""Response builders for the V5 interview engine.

Accept an ``InterviewBrain`` or a plain dict so the API shims and the
WebSocket handler can share one implementation. The underscore aliases at the
bottom keep the legacy import names working for tests (the original
``app/api/interview_v4.py`` module was deleted in the Phase 10 cleanup).
"""
from typing import Any, Union

from app.core.interview_brain import InterviewBrain
from app.core.interview_state import brain_to_dict

StateLike = Union[InterviewBrain, dict]


def _as_dict(state: StateLike) -> dict:
    return brain_to_dict(state) if isinstance(state, InterviewBrain) else state


def compose_conversation_turn(state: StateLike) -> str:
    """Compose the spoken message: acknowledgement + bridge + question."""
    s = _as_dict(state)
    turn = s.get("conversation_turn") or {}
    if isinstance(turn, dict) and turn.get("question"):
        parts = [
            p
            for p in (turn.get("acknowledgement", ""), turn.get("bridge", ""), turn["question"])
            if p
        ]
        return "\n\n".join(parts)
    return s.get("current_question", "")


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
    }


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
        "conversation_turn": compose_conversation_turn(s),
        "evaluation": {
            "scores": scored,
            "composite": s.get("evaluation_score"),
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
        "hiring_recommendation": s.get("hiring_recommendation", {}),
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


def build_report_response(state: StateLike) -> dict:
    """Build the final ``{type: report}`` payload on interview completion."""
    s = _as_dict(state)
    rec = s.get("hiring_recommendation", {})
    cs = s.get("competency_summary", {})
    graph = s.get("evidence_graph") or {}
    profile = s.get("difficulty_profile")

    report = {
        "status": "completed",
        "hiring_recommendation": {
            "verdict": rec.get("verdict", "insufficient_evidence"),
            "confidence": rec.get("confidence", 0.0),
            "composite_score": rec.get("composite_score"),
            "coverage_ratio": rec.get("coverage_ratio"),
        },
        "competency_summary": {
            comp: {
                "average_score": s_.get("average_score", 0.0),
                "evidence_count": s_.get("evidence_count", 0),
                "gap": s_.get("gap", 1.0),
            }
            for comp, s_ in cs.items()
        },
        "evidence_collected": len(s.get("evidence_store", [])),
        "questions_asked": s.get("question_number", 0),
        "hypothesis_outcomes": {
            "confirmed": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "confirmed"),
            "refuted": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "refuted"),
            "untested": sum(1 for h in (s.get("hypotheses") or []) if h.get("status") == "untested"),
        },
        "evidence_graph": {
            "competency_nodes": len((graph.get("nodes") or {})),
            "evidence_edges": len((graph.get("edges") or {})),
        },
        "difficulty_profile": profile,
        "hiring_decision": s.get("hiring_decision", {}),
    }
    return report


# Backward-compat aliases for any code that imported the underscore names.
_build_start_response = build_start_response
_build_answer_response = build_answer_response
_build_state_response = build_state_response
_build_report_response = build_report_response
_compose_conversation_turn = compose_conversation_turn
