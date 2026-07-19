"""
AI Interview Agent API - Clean Production API Endpoints
Provides modern, RESTful API for AI Interview Agent workflow.
"""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from app.orchestrators.interview_orchestrator import InterviewOrchestrator
from app.exceptions import SessionNotFoundException

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
    """Request model for starting a new interview."""
    company_id: int
    job_role: str
    candidate_id: str = ""
    total_questions: int = 10
    initial_difficulty: int = 1
    interview_type: str = "company"


class QuestionInitiateRequest(BaseModel):
    """Request model for initiating next question."""
    conversation_history: List[Dict[str, str]] = []
    current_phase: str = "intro"
    question_number: int = 0
    difficulty_level: int = 1
    candidate_profile: Dict[str, Any] = {}


class AnswerSubmitRequest(BaseModel):
    """Request model for submitting candidate answer."""
    question_number: int
    question: str
    candidate_answer: str
    conversation_history: List[Dict[str, str]] = []
    candidate_profile: Dict[str, Any] = {}
    difficulty_level: int = 1


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/interviews")
async def start_interview(request: InterviewStartRequest):
    """
    Start a new AI Interview Agent session.
    
    Body:
        company_id: Company ID
        job_role: Job role for interview
        candidate_id: Candidate identifier (optional)
        total_questions: Total questions to ask (default 10)
        initial_difficulty: Initial difficulty level 1-3 (default 1)
        interview_type: Type of interview ("company", "skill", "adaptive")
    
    Returns:
        Session initialization with session_id, phase, progress, etc.
    """
    try:
        result = await orchestrator.start_interview(
            company_id=request.company_id,
            job_role=request.job_role,
            candidate_id=request.candidate_id or str(request.company_id),
            total_questions=request.total_questions,
            initial_difficulty=request.initial_difficulty,
            interview_type=request.interview_type
        )
        
        logger.info(f"Created interview session: company_id={request.company_id}, session_id={result['session_id']}")
        return result
        
    except Exception as e:
        logger.exception("Failed to start interview")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interviews/{session_id}/questions/next")
async def initiate_next_question(
    session_id: str,
    request: QuestionInitiateRequest
):
    """
    Initiate the next question using LangGraph workflow.
    This will generate an AI question using company context.
    
    Path:
        session_id: Session UUID
    
    Body:
        conversation_history: Previous conversation entries
        current_phase: Current interview phase
        question_number: Current question number
        difficulty_level: Current difficulty level
        candidate_profile: Optional candidate profile data
    
    Returns:
        Generated question, next action, phase evolution, difficulty adjustment
    """
    try:
        result = await orchestrator.initiate_next_question(
            session_id=session_id,
            conversation_history=request.conversation_history,
            current_phase=request.current_phase,
            question_number=request.question_number,
            difficulty_level=request.difficulty_level,
            candidate_profile=request.candidate_profile
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
    request: AnswerSubmitRequest
):
    """
    Submit candidate answer for evaluation using LangGraph workflow.
    Evaluates answer, provides scoring, feedback, and determines next action.
    
    Path:
        session_id: Session UUID
    
    Body:
        question_number: Question number (already asked)
        question: The question that was asked
        candidate_answer: Candidate's answer text
        conversation_history: Conversation history
        candidate_profile: Optional candidate profile
        difficulty_level: Current difficulty level
    
    Returns:
        Evaluation results with scores, strengths, weaknesses, feedback,
        and suggested next_action
    """
    try:
        result = await orchestrator.submit_answer(
            session_id=session_id,
            question_number=request.question_number,
            question=request.question,
            candidate_answer=request.candidate_answer,
            conversation_history=request.conversation_history,
            candidate_profile=request.candidate_profile,
            difficulty_level=request.difficulty_level
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
async def get_session_status(session_id: str):
    """
    Get current session status.
    
    Path:
        session_id: Session UUID
    
    Returns:
        Current state: phase, progress, difficulty, elapsed time, etc.
    """
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
async def get_session_summary(session_id: str):
    """
    Get comprehensive session summary.
    Returns all questions, evaluations, and metrics.
    
    Path:
        session_id: Session UUID
    
    Returns:
        Complete summary with messages, evaluations, scores, recommendations
    """
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
async def get_rag_status(session_id: str):
    """
    Get RAG (Retrieval-Augmented Generation) metadata for session.
    Shows what company context was retrieved and how it was used.
    
    Path:
        session_id: Session UUID
    
    Returns:
        RAG metadata, namespace, documents retrieved, usage statistics
    """
    try:
        result = await orchestrator.get_session_status(session_id)
        
        # Add RAG specific metadata
        rag_info = {
            "rag_available": bool(result.get("rag_context_used")),
            "rag_details": {
                "company_id": result.get("rag_context_used"),
                "company_requirements": True
            }
        }
        
        return {**result, **rag_info}
        
    except SessionNotFoundException:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.exception("Failed to get RAG status")
        raise HTTPException(status_code=500, detail=str(e))