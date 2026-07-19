"""
Interview Orchestrator - Coordination Layer
Manages the interview session flow by coordinating between API requests and LangGraph agents.
"""
import logging
from typing import Dict, Any, Optional, List
from app.graph.interview_state import InterviewState
from app.graph.question_workflow import get_question_workflow
from app.graph.evaluation_workflow import get_evaluation_workflow
from app.services.repositories import get_session_repo, get_message_repo
from app.exceptions import SessionNotFoundException

logger = logging.getLogger(__name__)


class InterviewOrchestrator:
    """
    Orchestrator for Interview Agent workflow.
    Coordinates LangGraph execution and state management.
    """
    
    def __init__(self):
        """Initialize orchestrator."""
        self.session_repo = get_session_repo()
        self.message_repo = get_message_repo()
        self.question_workflow = None  # Will be loaded on demand
        self.evaluation_workflow = None  # Will be loaded on demand
    
    def get_question_workflow(self):
        """
        Get or create question generation workflow.
        
        Returns:
            Compiled StateGraph workflow
        """
        if self.question_workflow is None:
            from app.graph.question_workflow import get_question_workflow
            self.question_workflow = get_question_workflow()
        return self.question_workflow
    
    def get_evaluation_workflow(self):
        """
        Get or create evaluation workflow.
        
        Returns:
            Compiled StateGraph workflow
        """
        if self.evaluation_workflow is None:
            from app.graph.evaluation_workflow import get_evaluation_workflow
            self.evaluation_workflow = get_evaluation_workflow()
        return self.evaluation_workflow
    
    async def start_interview(
        self,
        company_id: int,
        job_role: str,
        candidate_id: Optional[str] = None,
        total_questions: int = 10,
        initial_difficulty: int = 1,
        interview_type: str = "company"
    ) -> Dict[str, Any]:
        """
        Start a new interview session.
        
        Args:
            company_id: Company ID
            job_role: Job role for interview
            candidate_id: Optional candidate identifier
            total_questions: Total questions to ask
            initial_difficulty: Initial difficulty level (1-3)
            interview_type: Type of interview
            
        Returns:
            dict: Session initialization response
        """
        logger.info(f"Starting interview: company_id={company_id}, job_role={job_role}")
        
        try:
            # Create session in database
            session = await self.session_repo.create_session(
                company_id=company_id,
                candidate_id=candidate_id,
                job_role=job_role,
                total_questions=total_questions,
                interview_type=interview_type
            )
            
            logger.info(f"Session created: {session['id']}")
            
            return {
                "session_id": session["id"],
                "status": "initialized",
                "current_phase": "intro",
                "question_number": 0,
                "total_questions": total_questions,
                "difficulty_level": initial_difficulty,
                "start_time": session.get("started_at")
            }
            
        except Exception as e:
            logger.error(f"Failed to start interview: {e}")
            raise
    
    async def initiate_next_question(
        self,
        session_id: str,
        conversation_history: List[Dict[str, str]],
        current_phase: str,
        question_number: int,
        difficulty_level: int,
        candidate_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initiate question generation using Question Generation workflow.
        
        Args:
            session_id: Session UUID
            conversation_history: List of conversation entries
            current_phase: Current interview phase
            question_number: Current question number
            difficulty_level: Current difficulty level
            candidate_profile: Optional candidate profile data
            
        Returns:
            dict: Generated question and next action
        """
        logger.info(f"Initiating next question: session={session_id}, phase={current_phase}, q#{question_number}")
        
        try:
            workflow = self.get_question_workflow()
            
            # Prepare initial state
            initial_state: InterviewState = {
                "session_id": session_id,
                "company_id": None,  # Will be loaded from database
                "candidate_id": str(session_id),  # Use session_id as temp candidate_id
                "job_role": None,  # Will be loaded from database
                "interview_type": None,  # Will be loaded from database
                "conversation_history": conversation_history,
                "current_phase": current_phase,
                "phase_stage": 0,
                "question_number": question_number,
                "total_questions": 10,  # Default, overrides later
                "difficulty_level": difficulty_level,
                "current_question": "",
                "company_context": [],
                "company_requirements": "",
                "rag_metadata": {},
                "candidate_answer": "",
                "evaluation_score": None,
                "technical_score": None,
                "communication_score": None,
                "strengths": [],
                "weaknesses": [],
                "feedback_detail": "",
                "evaluation_metadata": {},
                "evaluation_failed": False,
                "next_action": "continue",
                "suggested_follow_up": "",
                "next_phase": None,
                "next_difficulty": None,
                "start_time": None,
                "elapsed_time": None,
                "is_complete": False,
                "final_report": None,
                "nodes_executed": []
            }
            
            # Load session data for context
            session = await self.session_repo.get_session(session_id)
            initial_state["company_id"] = session.get("company_id")
            initial_state["candidate_id"] = session.get("candidate_id", str(session_id))
            initial_state["job_role"] = session.get("job_role")
            initial_state["interview_type"] = session.get("interview_type", "company")
            initial_state["total_questions"] = session.get("total_questions", 10)
            
            # Execute QUESTION GENERATION workflow only (no evaluation or decision)
            # This will return state after generating ONE question
            final_state = await workflow.ainvoke(initial_state, config={"recursion_limit": 50})
            
            # Extract question and state info
            question = final_state.get("current_question", "")
            new_question_number = final_state.get("question_number", question_number + 1)
            next_action = final_state.get("next_action", "continue")
            next_phase = final_state.get("next_phase", current_phase)
            next_difficulty = final_state.get("next_difficulty", difficulty_level)
            suggested_follow_up = final_state.get("suggested_follow_up", "")
            
            logger.info(f"Question generated: q#{new_question_number}, action={next_action}")
            
            return {
                "session_id": session_id,
                "question": question,
                "question_number": new_question_number,
                "phase": next_phase,
                "difficulty_level": next_difficulty,
                "next_action": next_action,
                "suggested_follow_up": suggested_follow_up,
                "rag_context_available": bool(final_state.get("company_requirements")),
                "nodes_executed": final_state.get("nodes_executed", []),
                "rag_metadata": final_state.get("rag_metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to generate next question: {e}")
            raise
    
    async def submit_answer(
        self,
        session_id: str,
        question_number: int,
        question: str,
        candidate_answer: str,
        conversation_history: List[Dict[str, str]],
        candidate_profile: Optional[Dict[str, Any]] = None,
        difficulty_level: int = 1
    ) -> Dict[str, Any]:
        """
        Submit candidate answer for evaluation using Evaluation workflow.
        
        Args:
            session_id: Session UUID
            question_number: Question number
            question: The question that was asked
            candidate_answer: Candidate's answer
            conversation_history: Conversation history
            candidate_profile: Optional candidate profile
            difficulty_level: Current difficulty level
            
        Returns:
            dict: Evaluation results
        """
        logger.info(f"Submitting answer for evaluation: session={session_id}, q#{question_number}")
        
        try:
            workflow = self.get_evaluation_workflow()
            
            # Prepare state for answer submission cycle
            initial_state: InterviewState = {
                "session_id": session_id,
                "company_id": None,
                "candidate_id": str(session_id),
                "job_role": None,
                "interview_type": None,
                "conversation_history": conversation_history,
                "current_phase": "intro",  # Loaded from session below
                "phase_stage": 0,
                "question_number": question_number + 1,  # Next question number (already asked)
                "total_questions": 10,
                "difficulty_level": difficulty_level,
                "current_question": question,
                "company_context": [],
                "company_requirements": "",
                "rag_metadata": {},
                "candidate_answer": candidate_answer,
                "evaluation_score": None,
                "technical_score": None,
                "communication_score": None,
                "strengths": [],
                "weaknesses": [],
                "feedback_detail": "",
                "evaluation_metadata": {},
                "evaluation_failed": False,
                "next_action": "continue",
                "suggested_follow_up": "",
                "next_phase": None,
                "next_difficulty": None,
                "start_time": None,
                "elapsed_time": None,
                "is_complete": False,
                "final_report": None,
                "nodes_executed": []
            }
            
            # Load session data
            session = await self.session_repo.get_session(session_id)
            initial_state["company_id"] = session.get("company_id")
            initial_state["candidate_id"] = session.get("candidate_id", str(session_id))
            initial_state["job_role"] = session.get("job_role")
            initial_state["interview_type"] = session.get("interview_type", "company")
            initial_state["candidate_profile"] = candidate_profile
            
            # Execute EVALUATION workflow only (no question generation)
            # This will return state after evaluating ONE answer
            final_state = await workflow.ainvoke(initial_state, config={"recursion_limit": 50})
            
            # Extract evaluation results
            evaluation_failed = final_state.get('evaluation_failed', False)
            
            if evaluation_failed:
                logger.error("Evaluation failed in workflow - returning error")
                return {
                    "session_id": session_id,
                    "question_number": question_number,
                    "evaluation_failed": True,
                    "evaluation": {
                        "score": None,
                        "technical_score": None,
                        "communication_score": None,
                        "strengths": [],
                        "weaknesses": [],
                        "feedback": "System error - evaluation could not be completed"
                    }
                }
            
            evaluation_score = final_state.get("evaluation_score", 0.0)
            technical_score = final_state.get("technical_score", 0.0)
            communication_score = final_state.get("communication_score", 0.0)
            strengths = final_state.get("strengths", [])
            weaknesses = final_state.get("weaknesses", [])
            feedback = final_state.get("feedback_detail", "")
            next_action = final_state.get("next_action", "continue")
            next_phase = final_state.get("next_phase", "intro")
            next_difficulty = final_state.get("next_difficulty", difficulty_level)
            
            logger.info(f"Answer evaluated: score={evaluation_score}, technical={technical_score}")
            
            # Store answer in database
            await self.message_repo.create_candidate_answer(
                session_id=session_id,
                role="candidate",
                candidate_answer=candidate_answer,
                question_number=question_number,
                phase=next_phase,
                score=evaluation_score
            )
            
            return {
                "session_id": session_id,
                "question_number": question_number,
                "evaluation": {
                    "score": evaluation_score,
                    "technical_score": technical_score,
                    "communication_score": communication_score,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "feedback": feedback
                },
                "next_phase": next_phase,
                "next_difficulty": next_difficulty,
                "next_action": next_action,
                "rag_context_used": bool(final_state.get("company_requirements")),
                "nodes_executed": final_state.get("nodes_executed", [])
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate answer: {e}")
            raise
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current session status.
        
        Args:
            session_id: Session UUID
            
        Returns:
            dict: Session status
        """
        try:
            session = await self.session_repo.get_session(session_id)
            messages = await self.message_repo.get_session_messages(session_id)
            
            return {
                "session_id": session_id,
                "status": session.get("status"),
                "current_phase": session.get("current_phase"),
                "question_number": session.get("current_question_number"),
                "total_questions": session.get("total_questions"),
                "difficulty_level": session.get("difficulty_level", 1),
                "elapsed_time": session.get("ended_at", None),
                "messages_count": len(messages)
            }
            
        except SessionNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            raise
    
    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive session summary.
        
        Args:
            session_id: Session UUID
            
        Returns:
            dict: Complete session summary
        """
        try:
            session = await self.session_repo.get_session(session_id)
            messages = await self.message_repo.get_session_messages(session_id)
            evaluations = await self.message_repo.get_evaluations(session_id)
            
            # Calculate metrics
            answered_questions = len([
                m for m in messages 
                if m.get("role") == "candidate" and m.get("question_number") < (session.get("current_question_number") or 0)
            ])
            total_questions_possible = session.get("total_questions", 10)
            
            scores = [float(e.get("score", 0)) for e in evaluations]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            return {
                "session_id": session_id,
                "company_id": session.get("company_id"),
                "job_role": session.get("job_role"),
                "status": session.get("status"),
                "current_phase": session.get("current_phase"),
                "question_number": session.get("current_question_number"),
                "total_questions": total_questions_possible,
                "final_score": round(avg_score, 2) if scores else None,
                "answered_ratio": round(answered_questions / total_questions_possible, 2) if total_questions_possible > 0 else 0,
                "total_questions_answered": answered_questions,
                "messages_count": len(messages),
                "evaluations_count": len(evaluations),
                "interview_complete": session.get("status") == "completed",
                "messages": messages,
                "evaluations": evaluations
            }
            
        except SessionNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to get session summary: {e}")
            raise
