"""
AI Interview Agent API - Clean Production API Endpoints
Provides modern, RESTful API for AI Interview Agent workflow.
Routes v3 (legacy) and v4 (evidence-driven) sessions to the correct engine.
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.candidates.auth import optional_candidate_auth
from app.database.session import get_session_factory
from app.models.db import CandidateProfile, InterviewSession
from app.orchestrators.interview_orchestrator import InterviewOrchestrator
from app.exceptions import SessionNotFoundException
from app.services.v4_session_store import get_v4_session_store
from app.config.interview_styles import get_style
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["AI Interview Agent"]
)

# ============================================================================
# ORCHESTRATOR INSTANCE
# ============================================================================

orchestrator = InterviewOrchestrator()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class InterviewStartRequest(BaseModel):
    department_id: Optional[int] = None
    job_role: str = ""
    total_questions: int = 10
    initial_difficulty: int = 1
    session_type: str = "department"
    interaction_mode: str = "avatar"
    scorecard_template_id: Optional[str] = None


class QuestionInitiateRequest(BaseModel):
    """Request model for initiating next question."""
    conversation_history: List[Dict[str, str]] = []
    current_phase: str = "intro"
    question_number: int = 0
    difficulty_level: int = 1
    candidate_profile: Dict[str, Any] = {}
    is_follow_up: bool = False


class AnswerSubmitRequest(BaseModel):
    """Request model for submitting candidate answer."""
    question_number: int
    question: str
    candidate_answer: str
    conversation_history: List[Dict[str, str]] = []
    candidate_profile: Dict[str, Any] = {}
    difficulty_level: int = 1
    is_follow_up: bool = False


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


async def _get_engine_version(session_id: str) -> str:
    async with get_session_factory()() as db:
        result = await db.execute(
            select(InterviewSession.engine_version).where(InterviewSession.id == UUID(session_id))
        )
        row = result.scalar_one_or_none()
        return row or "v3"


def _seed_v4_state(db_session: InterviewSession) -> None:
    store = get_v4_session_store()
    if store.get(str(db_session.id)):
        return

    style = get_style("STANDARD")
    state = {
        "session_id": str(db_session.id),
        "job_role": db_session.job_role or "Software Engineer",
        "department_id": db_session.department_id,
        "interview_style": style,
        "persona": style.get("persona", "friendly"),
        "difficulty_level": style.get("difficulty_range", (1, 3))[0],
        "candidate_profile": {
            "full_name": "Candidate",
            "headline": "",
            "strengths": [],
            "weaknesses": [],
        },
        "required_competencies": [c["id"] for c in COMPETENCY_TAXONOMY],
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
    store.set(str(db_session.id), state)


async def _run_v4_start(session_id: str, db_session: InterviewSession) -> dict:
    from app.agents.session_init_node import session_init_node
    from app.agents.company_context_node import department_context_node
    from app.agents.candidate_profile_node import candidate_profile_node
    from app.agents.competency_planner_node import competency_planner_node
    from app.agents.strategy_brain_node import strategy_brain_node
    from app.agents.hypothesis_node import hypothesis_node
    from app.agents.question_generator_node import question_generator_node

    store = get_v4_session_store()
    state = store.get_or_raise(session_id)

    state = session_init_node(state)
    state = await department_context_node(state)
    state = await candidate_profile_node(state)
    state = await competency_planner_node(state)
    state = await strategy_brain_node(state)
    state = await hypothesis_node(state)
    state = await question_generator_node(state)

    store.set(session_id, state)

    target = state.get("hypothesis_target", {})
    question = state.get("current_question", "")
    return {
        "session_id": session_id,
        "question": question,
        "question_number": state.get("question_number", 1),
        "phase": "v4_evidence_driven",
        "difficulty_level": state.get("difficulty_level", 1),
        "next_action": "continue",
        "is_follow_up": False,
        "suggested_follow_up": "",
        "rag_context_available": False,
        "nodes_executed": state.get("nodes_executed", []),
        "rag_metadata": {},
        "v4_hypothesis_target": target.get("statement", ""),
    }


async def _run_v4_answer(session_id: str, question: str, answer: str, conv_history: list) -> dict:
    from app.agents.unified_evaluator_node import unified_evaluator_node
    from app.agents.evidence_extractor_node import evidence_extractor_node
    from app.agents.reflection_engine import reflection_engine
    from app.agents.hypothesis_node import hypothesis_node
    from app.agents.question_generator_node import question_generator_node
    from app.agents.competency_planner_node import competency_planner_node
    from app.agents.action_router import route_after_planner

    store = get_v4_session_store()
    state = store.get_or_raise(session_id)

    conv = list(conv_history)
    if question:
        conv.append({"role": "assistant", "content": question})
    conv.append({"role": "user", "content": answer})

    state = {
        **state,
        "candidate_answer": answer,
        "conversation_history": conv,
        "skip_evaluation": False,
        "extracted_evidence": [],
    }

    state = await unified_evaluator_node(state)
    state = await evidence_extractor_node(state)
    state = await reflection_engine(state)

    action = state.get("reflection_action", "probe")

    if action == "change_competency":
        state = await competency_planner_node(state)
        if route_after_planner(state) == "finish":
            state = await _run_v4_synthesis(state)
            store.set(session_id, state)
            return _v4_eval_to_response(session_id, state, is_finished=True)
        state = await hypothesis_node(state)

    elif action == "finish":
        state = await _run_v4_synthesis(state)
        store.set(session_id, state)
        return _v4_eval_to_response(session_id, state, is_finished=True)

    state = await hypothesis_node(state)
    state = await question_generator_node(state)
    store.set(session_id, state)

    return _v4_eval_to_response(session_id, state, is_finished=False)


async def _run_v4_synthesis(state):
    from app.agents.synthesis_node import synthesis_node
    try:
        return await synthesis_node(state)
    except Exception as e:
        logger.warning(f"v4 synthesis failed (non-fatal): {type(e).__name__}")
    return state


def _v4_eval_to_response(session_id: str, state, is_finished: bool = False) -> dict:
    evaluation = state.get("unified_evaluation", {})
    scores = {}
    for dim, data in evaluation.items():
        if isinstance(data, dict) and data.get("score") is not None:
            scores[dim] = data["score"]

    composite = state.get("evaluation_score")
    avg = composite if composite is not None else (sum(scores.values()) / len(scores) if scores else 0)

    strengths = []
    weaknesses = []
    for dim, data in evaluation.items():
        if isinstance(data, dict):
            strengths.extend(data.get("strengths", []) or [])
            weaknesses.extend(data.get("weaknesses", []) or [])

    return {
        "session_id": session_id,
        "question_number": state.get("question_number", 0),
        "inquisitor_action": "saturate" if is_finished else "probe",
        "is_follow_up": False,
        "evaluation": {
            "score": round(float(avg), 2) if avg else 0,
            "technical_score": scores.get("technical", 0),
            "communication_score": scores.get("communication", 0),
            "strengths": strengths[:5],
            "weaknesses": weaknesses[:5],
            "feedback": f"Score: {round(float(avg), 2) if avg else 0}/10 across {len(scores)} dimensions",
        },
        "next_phase": "v4_evidence_driven",
        "next_difficulty": state.get("difficulty_level", 1),
        "next_action": "finish" if is_finished else "continue",
        "rag_context_used": False,
        "nodes_executed": state.get("nodes_executed", []),
        "v4_status": "completed" if is_finished else "in_progress",
        "v4_hypothesis_progress": {
            h.get("status", "untested"): sum(1 for h2 in (state.get("hypotheses") or []) if h2.get("status") == h.get("status"))
            for h in (state.get("hypotheses") or [])
        } if state.get("hypotheses") else {},
        "v4_competency_coverage": {
            comp: s.get("evidence_count", 0)
            for comp, s in (state.get("competency_summary") or {}).items()
        },
        "v4_next_question": state.get("current_question", "") if not is_finished else "",
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

@router.post("/interviews")
async def start_interview(request: InterviewStartRequest):
    """
    Start a new AI Interview Agent session.
    
    Body:
        department_id: Department ID
        job_role: Job role for interview
        candidate_id: Candidate identifier (optional)
        total_questions: Total questions to ask (default 10)
        initial_difficulty: Initial difficulty level 1-3 (default 1)
        session_type: Type of session ("department", "public", "mock")
    
    Returns:
        Session initialization with session_id, phase, progress, etc.
    """
    try:
        result = await orchestrator.start_interview(
            department_id=request.department_id,
            job_role=request.job_role,
            total_questions=request.total_questions,
            initial_difficulty=request.initial_difficulty,
            session_type=request.session_type,
            interaction_mode=request.interaction_mode,
            scorecard_template_id=request.scorecard_template_id,
        )
        
        logger.info(f"Created interview session: department_id={request.department_id}, session_id={result['session_id']}")
        return result
        
    except Exception as e:
        logger.exception("Failed to start interview")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interviews/{session_id}/questions/next")
async def initiate_next_question(
    session_id: str,
    request: QuestionInitiateRequest,
    current_candidate: Optional[CandidateProfile] = Depends(optional_candidate_auth),
):
    """
    Initiate the next question.
    Routes to v4 (evidence-driven) or v3 (legacy) engine based on session.engine_version.
    """
    db_session = await _verify_session_access(session_id, current_candidate)
    engine = db_session.engine_version or "v3"

    if engine == "v4":
        try:
            _seed_v4_state(db_session)
            result = await _run_v4_start(str(db_session.id), db_session)
            logger.info(f"v4 question generated: session={session_id}, q#{result['question_number']}")
            return result
        except Exception as e:
            logger.exception("v4 question generation failed, falling back to v3")
            engine = "v3"

    try:
        result = await orchestrator.initiate_next_question(
            session_id=session_id,
            conversation_history=request.conversation_history,
            current_phase=request.current_phase,
            question_number=request.question_number,
            difficulty_level=request.difficulty_level,
            candidate_profile=request.candidate_profile,
            is_follow_up=request.is_follow_up
        )
        
        logger.info(
            f"Question generated: session={session_id}, "
            f"q#{result['question_number']}, action={result['next_action']}"
        )
        return result
        
    except SessionNotFoundException:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.exception("Failed to generate next question")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interviews/{session_id}/answers")
async def submit_answer(
    session_id: str,
    request: AnswerSubmitRequest,
    current_candidate: Optional[CandidateProfile] = Depends(optional_candidate_auth),
):
    """
    Submit candidate answer for evaluation.
    Routes to v4 (evidence-driven) or v3 (legacy) engine based on session.engine_version.
    """
    db_session = await _verify_session_access(session_id, current_candidate)
    engine = db_session.engine_version or "v3"

    if engine == "v4":
        try:
            result = await _run_v4_answer(
                str(db_session.id),
                request.question,
                request.candidate_answer,
                request.conversation_history,
            )
            logger.info(
                f"v4 answer evaluated: session={session_id}, "
                f"q#{request.question_number}, v4_status={result.get('v4_status', 'in_progress')}"
            )
            return result
        except SessionNotFoundException:
            raise HTTPException(status_code=404, detail="Session not found")
        except Exception as e:
            logger.exception("v4 answer evaluation failed, falling back to v3")

    try:
        result = await orchestrator.submit_answer(
            session_id=session_id,
            question_number=request.question_number,
            question=request.question,
            candidate_answer=request.candidate_answer,
            conversation_history=request.conversation_history,
            candidate_profile=request.candidate_profile,
            difficulty_level=request.difficulty_level,
            is_follow_up=request.is_follow_up
        )
        
        logger.info(
            f"Answer evaluated: session={session_id}, "
            f"q#{request.question_number}, score={result['evaluation']['score']}"
        )
        return result
        
    except SessionNotFoundException:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.exception("Failed to evaluate answer")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interviews/{session_id}/status")
async def get_session_status(
    session_id: str,
    current_candidate: Optional[CandidateProfile] = Depends(optional_candidate_auth),
):
    """
    Get current session status.
    
    Path:
        session_id: Session UUID
    
    Returns:
        Current state: phase, progress, difficulty, elapsed time, etc.
    """
    await _verify_session_access(session_id, current_candidate)
    try:
        result = await orchestrator.get_session_status(session_id)
        return result
        
    except SessionNotFoundException:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.exception("Failed to get session status")
        raise HTTPException(status_code=500, detail=str(e))


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
        if v4_data:
            return v4_data

    try:
        result = await orchestrator.get_session_summary(session_id)
        return result
        
    except SessionNotFoundException:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.exception("Failed to get session summary")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interviews/{session_id}/rag-status")
async def get_rag_status(
    session_id: str,
    current_candidate: Optional[CandidateProfile] = Depends(optional_candidate_auth),
):
    """
    Get RAG (Retrieval-Augmented Generation) metadata for session.
    Shows what company context was retrieved and how it was used.
    
    Path:
        session_id: Session UUID
    
    Returns:
        RAG metadata, namespace, documents retrieved, usage statistics
    """
    await _verify_session_access(session_id, current_candidate)
    try:
        result = await orchestrator.get_session_status(session_id)
        
        # Add RAG specific metadata
        rag_info = {
            "rag_available": bool(result.get("rag_context_used")),
            "rag_details": {
                "department_id": result.get("rag_context_used"),
                "department_requirements": True
            }
        }
        
        return {**result, **rag_info}
        
    except SessionNotFoundException:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.exception("Failed to get RAG status")
        raise HTTPException(status_code=500, detail=str(e))