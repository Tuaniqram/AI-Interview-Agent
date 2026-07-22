"""
Interview Orchestrator - Coordination Layer
Manages the interview session flow by coordinating between API requests and LangGraph agents.
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from app.graph.interview_state import InterviewState
from app.graph.question_workflow import get_question_workflow
from app.graph.evaluation_workflow import get_evaluation_workflow
from app.services.repositories import get_session_repo, get_message_repo, get_evaluation_repo
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
        self.evaluation_repo = get_evaluation_repo()
        self.question_workflow = None
        self.evaluation_workflow = None
        self._pregen_cache: dict[str, dict] = {}
        self._pregen_pending: dict[str, asyncio.Task] = {}
    
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
        candidate_name: str = "",
        candidate_email: str = "",
        total_questions: int = 10,
        initial_difficulty: int = 1,
        interview_type: str = "company",
        interview_mode: str = "avatar"
    ) -> Dict[str, Any]:
        """
        Start a new interview session.
        """
        logger.info(f"Starting interview: company_id={company_id}, job_role={job_role}")
        
        try:
            session = await self.session_repo.create_session(
                company_id=company_id,
                candidate_id=candidate_id,
                candidate_name=candidate_name,
                candidate_email=candidate_email,
                job_role=job_role,
                total_questions=total_questions,
                interview_type=interview_type,
                interview_mode=interview_mode
            )
            
            logger.info(f"Session created: {session['id']}")

            return {
                "session_id": session["id"],
                "status": "initialized",
                "current_phase": "intro",
                "question_number": 1,
                "total_questions": total_questions,
                "difficulty_level": initial_difficulty,
                "start_time": session.get("started_at"),
                "interview_mode": interview_mode
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
        Initiate next question — checks pregen cache first, awaits background task if
        still running, falls back to live generation.
        Updates session table with current question number and phase.
        """
        if session_id in self._pregen_cache:
            result = self._pregen_cache.pop(session_id)
            self._pregen_pending.pop(session_id, None)
            logger.info(f"Using pre-generated question for session {session_id}, q#{result.get('question_number')}")
            await self._sync_session_state(session_id, result)
            return result

        task = self._pregen_pending.get(session_id)
        if task is not None and not task.done():
            logger.info(f"Waiting for background pre-generation for session {session_id}")
            try:
                await task
            except Exception:
                pass
            if session_id in self._pregen_cache:
                result = self._pregen_cache.pop(session_id)
                await self._sync_session_state(session_id, result)
                return result

        result = await self._do_generate_question(
            session_id, conversation_history, current_phase,
            question_number, difficulty_level, candidate_profile
        )
        await self._sync_session_state(session_id, result)
        return result

    async def _sync_session_state(self, session_id: str, result: Dict[str, Any]) -> None:
        """Persist question_number and phase from generated question to session table.

        Runs DB writes in parallel for performance since they're independent.
        """
        qnum = result.get("question_number")
        phase = result.get("phase")
        tasks = []
        if qnum is not None:
            tasks.append(self.session_repo.update_question_number(session_id, qnum))
        if phase is not None:
            tasks.append(self.session_repo.update_phase(session_id, phase))
        if tasks:
            await asyncio.gather(*tasks)

    async def _do_generate_question(
        self,
        session_id: str,
        conversation_history: List[Dict[str, str]],
        current_phase: str,
        question_number: int,
        difficulty_level: int,
        candidate_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate question using LangGraph workflow (no cache).
        """
        logger.info(f"Generating question: session={session_id}, phase={current_phase}, q#{question_number}")
        _t0 = time.time()
        
        try:
            workflow = self.get_question_workflow()
            _t1 = time.time()
            
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
            _t2 = time.time()
            
            # Execute QUESTION GENERATION workflow only (no evaluation or decision)
            # This will return state after generating ONE question
            final_state = await workflow.ainvoke(initial_state, config={
                "recursion_limit": 50,
                "configurable": {"thread_id": session_id},
            })
            _t3 = time.time()
            
            # Extract question and state info
            question = final_state.get("current_question", "")
            new_question_number = final_state.get("question_number", question_number)
            next_action = final_state.get("next_action", "continue")
            next_phase = final_state.get("next_phase", current_phase)
            next_difficulty = final_state.get("next_difficulty", difficulty_level)
            suggested_follow_up = final_state.get("suggested_follow_up", "")
            
            logger.info(
                f"Question generated: q#{new_question_number}, action={next_action} "
                f"[workflow_get={_t1-_t0:.2f}s, db_load={_t2-_t1:.2f}s, "
                f"workflow_run={_t3-_t2:.2f}s, total={_t3-_t0:.2f}s]"
            )
            
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

    async def _pregen_next_question_bg(
        self,
        session_id: str,
        conversation_history: List[Dict[str, str]],
        current_phase: str,
        question_number: int,
        difficulty_level: int,
        candidate_profile: Optional[Dict[str, Any]] = None
    ):
        """Pre-generate next question in background after evaluation completes."""
        try:
            result = await self._do_generate_question(
                session_id=session_id,
                conversation_history=conversation_history,
                current_phase=current_phase,
                question_number=question_number,
                difficulty_level=difficulty_level,
                candidate_profile=candidate_profile
            )
            self._pregen_cache[session_id] = result
            logger.info(f"Pre-generated question cached for session {session_id}, q#{result.get('question_number')}")
        except Exception as e:
            logger.warning(f"Pre-generation failed for session {session_id}: {e}")
        finally:
            self._pregen_pending.pop(session_id, None)
    
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
                "question_number": question_number,
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
            initial_state["current_phase"] = session.get("current_phase", "intro")
            initial_state["total_questions"] = session.get("total_questions", 10)
            initial_state["difficulty_level"] = session.get("difficulty_level", difficulty_level)
            initial_state["candidate_profile"] = candidate_profile
            
            # Execute EVALUATION workflow only (no question generation)
            # This will return state after evaluating ONE answer
            final_state = await workflow.ainvoke(initial_state, config={
                "recursion_limit": 50,
                "configurable": {"thread_id": session_id},
            })
            
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
            
            # Use the current session phase, not next_phase, for storing answered Q&A
            answered_phase = session.get("current_phase", "intro")
            
            # 1-2. Save question and answer in parallel
            question_task = self.message_repo.create_question(
                session_id=session_id,
                question_text=question,
                question_number=question_number,
                phase=answered_phase
            )
            answer_task = self.message_repo.create_candidate_answer(
                session_id=session_id,
                role="candidate",
                candidate_answer=candidate_answer,
                question_number=question_number,
                phase=answered_phase,
                score=evaluation_score
            )

            question_msg, answer_msg = await asyncio.gather(question_task, answer_task)
            
            # 3. Save structured evaluation to interview_evaluations
            try:
                await self.evaluation_repo.create_evaluation(
                    session_id=session_id,
                    message_id=answer_msg.get("id", ""),
                    technical_score=technical_score or 0.0,
                    communication_score=communication_score or 0.0,
                    strengths=", ".join(strengths) if strengths else None,
                    weaknesses=", ".join(weaknesses) if weaknesses else None,
                    feedback=feedback,
                    overall_score=evaluation_score
                )
            except Exception as e:
                logger.warning(f"Failed to save evaluation to interview_evaluations: {e}")
            
            # 4. If interview is finished, finalize the session
            if next_action == "finish":
                await self.session_repo.update_score(session_id, evaluation_score)
                await self.session_repo.complete_session(
                    session_id=session_id,
                    final_score=evaluation_score,
                    final_feedback=feedback
                )
                logger.info(f"Session {session_id} finalized with score={evaluation_score}")
            else:
                # Fire-and-forget: pre-generate the next question while candidate reads feedback
                if session_id not in self._pregen_pending:
                    task = asyncio.create_task(self._pregen_next_question_bg(
                        session_id=session_id,
                        conversation_history=conversation_history + [
                            {"role": "assistant", "content": question},
                            {"role": "user", "content": candidate_answer}
                        ],
                        current_phase=next_phase,
                        question_number=question_number + 1,
                        difficulty_level=next_difficulty,
                        candidate_profile=candidate_profile
                    ))
                    self._pregen_pending[session_id] = task
            
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
            session_task = self.session_repo.get_session(session_id)
            messages_task = self.message_repo.get_session_messages(session_id)
            session, messages = await asyncio.gather(session_task, messages_task)
            
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
            session_task = self.session_repo.get_session(session_id)
            messages_task = self.message_repo.get_session_messages(session_id)
            session, messages = await asyncio.gather(session_task, messages_task)
            
            # Get structured evaluations from interview_evaluations table
            try:
                evaluations = await self.evaluation_repo.get_evaluations_by_session(session_id)
            except Exception:
                evaluations = []
            
            # Calculate metrics
            answered_questions = len([
                m for m in messages 
                if m.get("role") == "candidate"
            ])
            total_questions_possible = session.get("total_questions", 10)
            
            # Use evaluations if available, fallback to message scores
            if evaluations:
                scores = [float(e.get("score", 0)) for e in evaluations]
                technical_scores = [float(e.get("technical_score", 0)) for e in evaluations if e.get("technical_score")]
                comm_scores = [float(e.get("communication_score", 0)) for e in evaluations if e.get("communication_score")]
            else:
                message_evals = await self.message_repo.get_evaluations(session_id)
                scores = [float(e.get("score", 0)) for e in message_evals]
                technical_scores = []
                comm_scores = []
            
            avg_score = sum(scores) / len(scores) if scores else (session.get("final_score") or 0)
            avg_technical = sum(technical_scores) / len(technical_scores) if technical_scores else None
            avg_communication = sum(comm_scores) / len(comm_scores) if comm_scores else None
            
            # Aggregate strengths and weaknesses
            all_strengths = []
            all_weaknesses = []
            for e in evaluations:
                if e.get("strengths"):
                    all_strengths.extend([s.strip() for s in e["strengths"].split(",") if s.strip()])
                if e.get("weaknesses"):
                    all_weaknesses.extend([w.strip() for w in e["weaknesses"].split(",") if w.strip()])
            
            return {
                "session_id": session_id,
                "company_id": session.get("company_id"),
                "candidate_name": session.get("candidate_name", ""),
                "candidate_email": session.get("candidate_email", ""),
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
                "answered_ratio": round(answered_questions / total_questions_possible, 2) if total_questions_possible > 0 else 0,
                "total_questions_answered": answered_questions,
                "messages_count": len(messages),
                "evaluations_count": len(evaluations),
                "interview_complete": session.get("status") == "completed",
                "started_at": session.get("started_at"),
                "ended_at": session.get("ended_at"),
                "messages": messages,
                "evaluations": evaluations
            }
            
        except SessionNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to get session summary: {e}")
            raise
