import logging
from typing import Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.candidates.auth import optional_candidate_auth
from app.database.deps import get_db
from app.database.session import get_session_factory
from app.graph.interview_state import InterviewState
from app.models.db import CandidateProfile, InterviewSession
from app.config.interview_styles import get_style, list_styles
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.data.competency_resolver import (
    default_taxonomy,
    resolve_competencies,
    taxonomy_for_state,
)
from app.agents.session_init_node import session_init_node
from app.agents.company_context_node import department_context_node
from app.agents.candidate_profile_node import candidate_profile_node
from app.agents.competency_planner_node import competency_planner_node
from app.agents.strategy_brain_node import strategy_brain_node
from app.agents.hypothesis_node import hypothesis_node
from app.agents.question_generator_node import question_generator_node
from app.agents.unified_evaluator_node import unified_evaluator_node
from app.agents.evidence_extractor_node import evidence_extractor_node
from app.agents.reflection_engine import reflection_engine
from app.agents.action_router import route, route_after_planner
from app.agents.synthesis_node import synthesis_node
from app.exceptions import SessionNotFoundException
from app.services.v4_session_store import get_v4_session_store
from app.utils.input_sanitizer import sanitize_user_input, detect_prompt_injection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interviews/v4", tags=["AI Interview Agent v4"])

_store = get_v4_session_store()

# Styles/competencies don't need DB writes — safe to return regardless of DB
_STYLE_NAMES = {s["name"] for s in list_styles()}
_VALID_STYLE_NAMES = _STYLE_NAMES if _STYLE_NAMES else {"STANDARD"}
_COMPETENCY_IDS = {c["id"] for c in COMPETENCY_TAXONOMY}


# ============================================================================
# SCHEMAS
# ============================================================================


class V4StartRequest(BaseModel):
    job_role: str = Field(default="Software Engineer", min_length=1, max_length=200)
    style_name: str = Field(default="STANDARD", min_length=1, max_length=50)
    candidate_name: str = Field(default="", max_length=200)
    candidate_headline: str = Field(default="", max_length=500)
    candidate_strengths: list[str] = Field(default_factory=list, max_length=20)
    candidate_weaknesses: list[str] = Field(default_factory=list, max_length=20)
    department_id: int | None = None

    @field_validator("style_name")
    @classmethod
    def validate_style(cls, v: str) -> str:
        if v.upper() not in _VALID_STYLE_NAMES and v not in _VALID_STYLE_NAMES:
            valid = ", ".join(sorted(_VALID_STYLE_NAMES))
            raise ValueError(f"Unknown style '{v}'. Valid: {valid}")
        return v.upper()

    @field_validator("candidate_strengths", "candidate_weaknesses")
    @classmethod
    def validate_list_items(cls, v: list[str]) -> list[str]:
        return [s.strip()[:100] for s in v if s.strip()]


class V4AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Answer cannot be empty")
        return stripped


class V4StyleInfoResponse(BaseModel):
    name: str
    persona: str
    max_questions: int
    difficulty_range: list[int]


# ============================================================================
# HELPERS
# ============================================================================


async def _get_session_or_404(session_id: str) -> InterviewState:
    try:
        return _store.get_or_raise(session_id)
    except SessionNotFoundException:
        raise HTTPException(status_code=404, detail=f"Session '{session_id[:12]}...' not found")


def _validate_uuid(session_id: str) -> str:
    try:
        UUID(session_id)
        return session_id
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid session_id format: '{session_id[:20]}'")


async def _verify_v4_access(
    session_id: str,
    current_candidate: Optional[CandidateProfile],
) -> None:
    async with get_session_factory()() as db:
        result = await db.execute(
            select(InterviewSession).where(InterviewSession.id == UUID(session_id))
        )
        db_session = result.scalar_one_or_none()
    if not db_session:
        return
    if db_session.candidate_profile_id is not None:
        if not current_candidate:
            raise HTTPException(status_code=401, detail="Authentication required")
        if str(db_session.candidate_profile_id) != str(current_candidate.id):
            raise HTTPException(status_code=403, detail="You don't own this session")


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/styles")
async def list_interview_styles():
    styles = list_styles()
    return {
        "styles": [
            V4StyleInfoResponse(
                name=s.get("name", ""),
                persona=s.get("persona", "friendly"),
                max_questions=s.get("max_questions", 10),
                difficulty_range=list(s.get("difficulty_range", (1, 3))),
            )
            for s in styles
        ]
    }


@router.get("/competencies")
async def list_competencies():
    return {
        "competencies": [
            {"id": c["id"], "name": c["name"], "category": c["category"]}
            for c in COMPETENCY_TAXONOMY
        ]
    }


@router.post("/start")
async def start_v4_interview(request: V4StartRequest):
    session_id = str(uuid4())
    style = get_style(request.style_name)

    taxonomy = default_taxonomy()
    if request.department_id:
        async with get_session_factory()() as db:
            taxonomy = await resolve_competencies(db, department_id=request.department_id)
    competency_taxonomy, required, domain_label = taxonomy_for_state(taxonomy)

    state: InterviewState = _build_initial_state(
        session_id, request, style, competency_taxonomy, required, domain_label
    )

    try:
        state = session_init_node(state)
        state = await department_context_node(state)
        state = await candidate_profile_node(state)
        state = await competency_planner_node(state)
        state = await strategy_brain_node(state)
        state = await hypothesis_node(state)
        state = await question_generator_node(state)

        _store.set(session_id, state)
        logger.info(f"v4 session started: {session_id[:12]}..., style={request.style_name}, role={request.job_role}")

        return _build_start_response(session_id, state)
    except Exception as e:
        _store.pop(session_id)
        logger.exception(f"Failed to start v4 interview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {type(e).__name__}")


@router.post("/{session_id}/answer")
async def submit_v4_answer(session_id: str, request: V4AnswerRequest):
    _validate_uuid(session_id)
    state = await _get_session_or_404(session_id)

    sanitized = sanitize_user_input(request.answer)
    injections = detect_prompt_injection(request.answer)
    if injections:
        logger.warning(f"Potential prompt injection detected in session {session_id[:12]}: {injections[:3]}")
    request.answer = sanitized

    question = state.get("current_question", "")
    question_number = state.get("question_number", 0)
    max_questions = state.get("max_questions", 20)

    if question_number >= max_questions:
        return _build_report_response(state)

    conv = list(state.get("conversation_history", []))
    if question:
        conv.append({"role": "assistant", "content": question})
    conv.append({"role": "user", "content": request.answer})

    state = {
        **state,
        "candidate_answer": request.answer,
        "conversation_history": conv,
        "skip_evaluation": False,
        "extracted_evidence": [],
    }

    try:
        state = await unified_evaluator_node(state)
        state = await evidence_extractor_node(state)
        state = await reflection_engine(state)

        action = state.get("reflection_action", "probe")

        if action == "change_competency":
            state = await competency_planner_node(state)
            routed = route_after_planner(state)
            if routed == "finish":
                return await _finalize_session(session_id, state)

            state = await hypothesis_node(state)

        elif action == "finish":
            return await _finalize_session(session_id, state)

        state = await hypothesis_node(state)
        state = await question_generator_node(state)

        _store.set(session_id, state)
        logger.info(f"v4 answer processed: session={session_id[:12]}..., q#{question_number}, action={action}")

        return _build_answer_response(session_id, state)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to process answer: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Error processing answer: {type(e).__name__}")


async def _finalize_session(session_id: str, state: InterviewState) -> dict:
    try:
        state = await synthesis_node(state)
    except Exception as e:
        logger.warning(f"Synthesis failed (non-fatal): {type(e).__name__}")
    _store.set(session_id, state)
    report = _build_report_response(state)
    report["interview_complete"] = True
    return report


@router.get("/{session_id}/state")
async def get_v4_state(
    session_id: str,
    current_candidate: Optional[CandidateProfile] = Depends(optional_candidate_auth),
):
    _validate_uuid(session_id)
    await _verify_v4_access(session_id, current_candidate)
    state = await _get_session_or_404(session_id)
    return _build_state_response(session_id, state)


@router.get("/{session_id}/report")
async def get_v4_report(
    session_id: str,
    current_candidate: Optional[CandidateProfile] = Depends(optional_candidate_auth),
):
    _validate_uuid(session_id)
    await _verify_v4_access(session_id, current_candidate)
    state = await _get_session_or_404(session_id)
    return _build_report_response(state)


# ============================================================================
# STATE BUILDERS
# ============================================================================


def _build_initial_state(
    session_id: str,
    request: V4StartRequest,
    style: dict,
    competency_taxonomy: list[dict],
    required_competencies: list[str],
    domain_label: str,
) -> InterviewState:
    return {
        "session_id": session_id,
        "job_role": request.job_role,
        "department_id": request.department_id,
        "interview_style": style,
        "persona": style.get("persona", "friendly"),
        "difficulty_level": style.get("difficulty_range", (1, 3))[0],
        "candidate_profile": {
            "full_name": request.candidate_name or "Candidate",
            "headline": request.candidate_headline or "",
            "strengths": request.candidate_strengths,
            "weaknesses": request.candidate_weaknesses,
        },
        "competency_taxonomy": competency_taxonomy,
        "domain_label": domain_label,
        "required_competencies": required_competencies,
        "conversation_history": [],
        "question_number": 0,
        "current_question": "",
        "candidate_answer": "",
        "flow_type": "v4_evidence_driven",
        "nodes_executed": [],
        "start_time": datetime.now(timezone.utc).isoformat(),
        "hypotheses": [],
        "hypothesis_target": None,
        "evidence_store": [],
        "competency_summary": {},
        "unified_evaluation": {},
        "evaluation_score": None,
        "observations": [],
        "competency_plan": [],
        "next_competency": None,
        "interview_strategy": {},
        "reflection_action": "probe",
        "evidence_sufficiency": {},
        "hiring_recommendation": {},
        "contradictions": [],
        "consistency_checks": [],
        "extracted_evidence": [],
        "max_questions": style.get("max_questions", 20),
        "questions_asked": [],
        "question_objective": {},
        "skip_evaluation": False,
        "evaluator_mode": style.get("evaluator_mode", "unified"),
        "strategy_cache_valid": False,
    }


def _build_start_response(session_id: str, state: InterviewState) -> dict:
    target = state.get("hypothesis_target", {})
    question = state.get("current_question", "")
    next_comp = state.get("next_competency", {})
    comp_id = next_comp.get("id", "") if isinstance(next_comp, dict) else ""

    return {
        "session_id": session_id,
        "status": "in_progress",
        "question": {
            "text": question,
            "number": state.get("question_number", 1),
            "target_competency": target.get("competency", comp_id),
            "target_hypothesis": target.get("statement", ""),
        },
        "hypothesis_target": {
            "statement": target.get("statement", ""),
            "confidence": target.get("confidence", 0.0),
            "status": target.get("status", "untested"),
        } if target else None,
        "persona": state.get("persona", "friendly"),
        "difficulty": state.get("difficulty_level", 1),
        "competencies": {
            "planned": len(state.get("required_competencies", [])),
            "next": comp_id,
        },
    }


def _build_answer_response(session_id: str, state: InterviewState) -> dict:
    evaluation = state.get("unified_evaluation", {})
    target = state.get("hypothesis_target", {})
    next_comp = state.get("next_competency", {})

    scored = {}
    for dim, data in evaluation.items():
        if isinstance(data, dict) and data.get("score") is not None:
            scored[dim] = {
                "score": data["score"],
                "evidence": (data.get("evidence", "") or "")[:200],
                "strengths": data.get("strengths", []),
                "weaknesses": data.get("weaknesses", []),
            }

    cs = state.get("competency_summary", {})
    competency_progress = {}
    for comp_id, summary in cs.items():
        competency_progress[comp_id] = {
            "evidence_count": summary.get("evidence_count", 0),
            "average_score": summary.get("average_score", 0.0),
            "gap": summary.get("gap", 1.0),
        }

    hyp_statuses = {}
    for h in (state.get("hypotheses") or []):
        st = h.get("status", "untested")
        hyp_statuses[st] = hyp_statuses.get(st, 0) + 1

    next_question = state.get("current_question", "")
    next_comp_id = next_comp.get("id", "") if isinstance(next_comp, dict) else ""

    return {
        "session_id": session_id,
        "status": "in_progress",
        "evaluation": {
            "scores": scored,
            "composite": state.get("evaluation_score"),
        },
        "next_question": {
            "text": next_question,
            "number": state.get("question_number", 0),
            "target_competency": target.get("competency", next_comp_id),
        },
        "evidence": {
            "total": len(state.get("evidence_store", [])),
            "competencies_covered": len(competency_progress),
            "competency_progress": competency_progress,
        },
        "hypothesis_progress": {
            "total": len(state.get("hypotheses", [])),
            "statuses": hyp_statuses,
        },
        "contradictions": len(state.get("contradictions", [])),
        "hiring_recommendation": state.get("hiring_recommendation", {}),
    }


def _build_state_response(session_id: str, state: InterviewState) -> dict:
    return {
        "session_id": session_id,
        "question_number": state.get("question_number", 0),
        "persona": state.get("persona", ""),
        "difficulty": state.get("difficulty_level", 1),
        "evidence_count": len(state.get("evidence_store", [])),
        "competency_coverage": {
            comp: s.get("evidence_count", 0)
            for comp, s in (state.get("competency_summary") or {}).items()
        },
        "hypothesis_summary": {
            "total": len(state.get("hypotheses", [])),
            "confirmed": sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "confirmed"),
            "refuted": sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "refuted"),
            "testing": sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "testing"),
        },
        "contradictions": len(state.get("contradictions", [])),
        "hiring_recommendation": state.get("hiring_recommendation", {}),
        "current_question": state.get("current_question", ""),
        "evaluation_score": state.get("evaluation_score"),
    }


def _build_report_response(state: InterviewState) -> dict:
    rec = state.get("hiring_recommendation", {})
    cs = state.get("competency_summary", {})

    return {
        "status": "completed",
        "hiring_recommendation": {
            "verdict": rec.get("verdict", "insufficient_evidence"),
            "confidence": rec.get("confidence", 0.0),
            "composite_score": rec.get("composite_score"),
            "coverage_ratio": rec.get("coverage_ratio"),
        },
        "competency_summary": {
            comp: {
                "average_score": s.get("average_score", 0.0),
                "evidence_count": s.get("evidence_count", 0),
                "gap": s.get("gap", 1.0),
            }
            for comp, s in cs.items()
        },
        "evidence_collected": len(state.get("evidence_store", [])),
        "questions_asked": state.get("question_number", 0),
        "hypothesis_outcomes": {
            "confirmed": sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "confirmed"),
            "refuted": sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "refuted"),
            "untested": sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "untested"),
        },
    }
