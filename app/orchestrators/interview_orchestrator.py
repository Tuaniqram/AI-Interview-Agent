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
    Handles multi-turn follow-up probing via the inquisitor node.
    """

    def __init__(self):
        self.session_repo = get_session_repo()
        self.message_repo = get_message_repo()
        self.evaluation_repo = get_evaluation_repo()
        self.question_workflow = None
        self.evaluation_workflow = None
        self._pregen_cache: dict[str, dict] = {}
        self._pregen_pending: dict[str, asyncio.Task] = {}
        self._probe_state: dict[str, dict] = {}

    def get_question_workflow(self):
        if self.question_workflow is None:
            from app.graph.question_workflow import get_question_workflow
            self.question_workflow = get_question_workflow()
        return self.question_workflow

    def get_evaluation_workflow(self):
        if self.evaluation_workflow is None:
            from app.graph.evaluation_workflow import get_evaluation_workflow
            self.evaluation_workflow = get_evaluation_workflow()
        return self.evaluation_workflow

    async def start_interview(
        self,
        department_id: Optional[int] = None,
        job_role: str = "",
        total_questions: int = 10,
        initial_difficulty: int = 1,
        session_type: str = "department",
        interaction_mode: str = "avatar",
        candidate_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Starting interview: department_id={department_id}, job_role={job_role}")

        try:
            session = await self.session_repo.create_session(
                department_id=department_id,
                job_role=job_role,
                total_questions=total_questions,
                session_type=session_type,
                interaction_mode=interaction_mode,
                candidate_profile_id=candidate_id,
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
                "interaction_mode": interaction_mode
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
        candidate_profile: Optional[Dict[str, Any]] = None,
        is_follow_up: bool = False,
    ) -> Dict[str, Any]:
        """
        Initiate next question — supports both main questions and probe follow-ups.

        For probes (is_follow_up=True): generates a targeted follow-up using probe_angle
        For main questions: normal flow with pregen cache check
        """
        if is_follow_up:
            return await self._generate_probe_question(
                session_id, conversation_history, current_phase,
                question_number, difficulty_level, candidate_profile
            )

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

    async def _generate_probe_question(
        self,
        session_id: str,
        conversation_history: List[Dict[str, str]],
        current_phase: str,
        question_number: int,
        difficulty_level: int,
        candidate_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a probe follow-up question based on inquisitor's decision."""
        probe = self._probe_state.get(session_id, {})
        probe_angle = probe.get('probe_angle', '')
        main_question = probe.get('main_question', '')
        probing_history = probe.get('probing_history', [])

        from app.services.llm_service import get_llm_service

        last_answer = ""
        for h in reversed(conversation_history):
            if h.get('role') == 'user' and not last_answer:
                last_answer = h.get('content', '')
                break

        probe_prompt = f"""You are a professional interviewer conducting a follow-up probe.

Main question asked: {main_question}
Probe angle: {probe_angle}
Candidate's last answer: {last_answer[:600] if last_answer else 'N/A'}
Previous follow-ups on this topic:
{chr(10).join(f"- Q{i+1}: {p.get('question', '')[:100]}" for i, p in enumerate(probing_history[-3:]))}

Generate ONE conversational follow-up question that:
1. Connects naturally to the candidate's last answer
2. Probes the specific angle described above
3. Is 1-2 sentences, open-ended
4. Stays on the SAME topic as the main question
5. Does NOT repeat any previous probes

Output ONLY the question text, no prefix, no explanation."""

        try:
            question = await get_llm_service().invoke(
                prompt=probe_prompt,
                temperature=0.7,
                max_tokens=200
            )
            question = question.strip()
            if question.startswith("Question:"):
                question = question[9:].strip()
        except Exception as e:
            logger.warning(f"Probe generation failed: {e}")
            question = probe_angle or "Can you tell me more about that?"

        if not question:
            question = "Can you elaborate on that?"

        depth = probe.get('depth', 0) + 1

        probing_history.append({
            'question': question,
            'depth': depth,
        })

        self._probe_state[session_id] = {
            **probe,
            'probing_history': probing_history,
            'depth': depth,
        }

        logger.info(f"Generated probe question (depth={depth}): {question[:80]}...")

        return {
            "session_id": session_id,
            "question": question,
            "question_number": question_number,
            "phase": current_phase,
            "difficulty_level": difficulty_level,
            "next_action": "probe",
            "is_follow_up": True,
            "probe_depth": depth,
            "suggested_follow_up": probe_angle,
            "rag_context_available": False,
            "nodes_executed": ["probe_generation"],
            "rag_metadata": {}
        }

    async def _sync_session_state(self, session_id: str, result: Dict[str, Any]) -> None:
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
        logger.info(f"Generating question: session={session_id}, phase={current_phase}, q#{question_number}")
        _t0 = time.time()

        try:
            workflow = self.get_question_workflow()
            _t1 = time.time()

            initial_state: InterviewState = {
                "session_id": session_id,
                "department_id": None,
                "candidate_id": str(session_id),
                "job_role": None,
                "flow_type": None,
                "conversation_history": conversation_history,
                "current_phase": current_phase,
                "phase_stage": 0,
                "question_number": question_number,
                "total_questions": 10,
                "difficulty_level": difficulty_level,
                "current_question": "",
                "question_depth": 0,
                "follow_up_count": 0,
                "topic_saturated": False,
                "probe_question": "",
                "probe_angle": "",
                "inquisitor_action": "main",
                "is_follow_up": False,
                "main_question": "",
                "probing_history": [],
                "skills_tested": [],
                "skills_weak": [],
                "skills_uncovered": [],
                "coverage_map": {},
                "speech_metrics": {},
                "department_context": [],
                "department_requirements": "",
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

            session = await self.session_repo.get_session(session_id)
            initial_state["department_id"] = session.get("department_id")
            initial_state["candidate_id"] = session.get("candidate_id", str(session_id))
            initial_state["job_role"] = session.get("job_role")
            initial_state["flow_type"] = session.get("session_type", "department")
            initial_state["total_questions"] = session.get("total_questions", 10)
            _t2 = time.time()

            final_state = await workflow.ainvoke(initial_state, config={
                "recursion_limit": 50,
                "configurable": {"thread_id": session_id},
            })
            _t3 = time.time()

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
                "is_follow_up": False,
                "suggested_follow_up": suggested_follow_up,
                "rag_context_available": bool(final_state.get("department_requirements")),
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
        difficulty_level: int = 1,
        is_follow_up: bool = False,
    ) -> Dict[str, Any]:
        """
        Submit candidate answer for evaluation.

        Handles multi-turn probing:
        - If inquisitor says "probe": return probe question, don't save to DB yet
        - If inquisitor says "saturate": save main Q&A + all probes to DB
        """
        logger.info(f"Submitting answer: session={session_id}, q#{question_number}, follow_up={is_follow_up}")

        try:
            workflow = self.get_evaluation_workflow()

            # Load state for probe context
            probe = self._probe_state.get(session_id, {})
            probing_history = probe.get('probing_history', [])
            question_depth = probe.get('depth', 0) if is_follow_up else 0
            main_question = probe.get('main_question', question)

            initial_state: InterviewState = {
                "session_id": session_id,
                "department_id": None,
                "candidate_id": str(session_id),
                "job_role": None,
                "flow_type": None,
                "conversation_history": conversation_history,
                "current_phase": "intro",
                "phase_stage": 0,
                "question_number": question_number,
                "total_questions": 10,
                "difficulty_level": difficulty_level,
                "current_question": question,
                "question_depth": question_depth,
                "follow_up_count": len(probing_history),
                "topic_saturated": False,
                "probe_question": "",
                "probe_angle": probe.get('probe_angle', ''),
                "inquisitor_action": "main",
                "is_follow_up": is_follow_up,
                "main_question": main_question,
                "probing_history": probing_history,
                "skills_tested": [],
                "skills_weak": [],
                "skills_uncovered": [],
                "coverage_map": {},
                "speech_metrics": {},
                "department_context": [],
                "department_requirements": "",
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

            session = await self.session_repo.get_session(session_id)
            initial_state["department_id"] = session.get("department_id")
            initial_state["candidate_id"] = session.get("candidate_id", str(session_id))
            initial_state["job_role"] = session.get("job_role")
            initial_state["flow_type"] = session.get("session_type", "department")
            initial_state["current_phase"] = session.get("current_phase", "intro")
            initial_state["total_questions"] = session.get("total_questions", 10)
            initial_state["difficulty_level"] = session.get("difficulty_level", difficulty_level)
            initial_state["candidate_profile"] = candidate_profile

            final_state = await workflow.ainvoke(initial_state, config={
                "recursion_limit": 50,
                "configurable": {"thread_id": session_id},
            })

            evaluation_failed = final_state.get('evaluation_failed', False)

            if evaluation_failed:
                logger.error("Evaluation failed in workflow")
                return {
                    "session_id": session_id,
                    "question_number": question_number,
                    "evaluation_failed": True,
                    "is_follow_up": is_follow_up,
                    "evaluation": {
                        "score": None, "technical_score": None, "communication_score": None,
                        "strengths": [], "weaknesses": [],
                        "feedback": "System error - evaluation could not be completed"
                    }
                }

            evaluation_score = final_state.get("evaluation_score", 0.0)
            technical_score = final_state.get("technical_score", 0.0)
            communication_score = final_state.get("communication_score", 0.0)
            strengths = final_state.get("strengths", [])
            weaknesses = final_state.get("weaknesses", [])
            feedback = final_state.get("feedback_detail", "")
            inquisitor_action = final_state.get("inquisitor_action", "saturate")
            probe_angle = final_state.get("probe_angle", "")
            next_action = final_state.get("next_action", "continue")
            next_phase = final_state.get("next_phase", session.get("current_phase", "intro"))
            next_difficulty = final_state.get("next_difficulty", difficulty_level)

            logger.info(f"Answer evaluated: score={evaluation_score}, inquisitor={inquisitor_action}")

            # ── Probe flow: don't save to DB, return probe question ──
            if inquisitor_action == "probe":
                self._probe_state[session_id] = {
                    'main_question': main_question,
                    'probe_angle': probe_angle,
                    'probing_history': probing_history,
                    'depth': question_depth,
                }

                return {
                    "session_id": session_id,
                    "question_number": question_number,
                    "inquisitor_action": "probe",
                    "probe_angle": probe_angle,
                    "is_follow_up": True,
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
                    "next_action": "probe",
                }

            # ── Saturate: save all Q&A to DB ──
            answered_phase = session.get("current_phase", "intro")

            # Save main question if this is the first answer or a follow-up completing the topic
            save_tasks = []

            if not is_follow_up:
                save_tasks.append(self.message_repo.create_question(
                    session_id=session_id,
                    question_text=question,
                    question_number=question_number,
                    phase=answered_phase
                ))
            else:
                # Save each probe question-answer pair
                for i, p in enumerate(probing_history):
                    p_q = p.get('question', '')
                    if p_q:
                        save_tasks.append(self.message_repo.create_question(
                            session_id=session_id,
                            question_text=p_q,
                            question_number=question_number,
                            phase=answered_phase,
                            is_follow_up=True,
                            follow_up_number=i + 1,
                        ))

            # Save the final answer for this question
            answer_task = self.message_repo.create_candidate_answer(
                session_id=session_id,
                role="candidate",
                candidate_answer=candidate_answer,
                question_number=question_number,
                phase=answered_phase,
                score=evaluation_score,
                is_follow_up=is_follow_up,
                follow_up_number=len(probing_history) + 1 if is_follow_up else 0,
            )

            if save_tasks:
                await asyncio.gather(*save_tasks)
            question_msg = await answer_task

            # Save evaluation
            try:
                await self.evaluation_repo.create_evaluation(
                    session_id=session_id,
                    message_id=question_msg.get("id", ""),
                    technical_score=technical_score or 0.0,
                    communication_score=communication_score or 0.0,
                    strengths=", ".join(strengths) if strengths else None,
                    weaknesses=", ".join(weaknesses) if weaknesses else None,
                    feedback=feedback,
                    overall_score=evaluation_score
                )
            except Exception as e:
                logger.warning(f"Failed to save evaluation: {e}")

            # Clean up probe state
            self._probe_state.pop(session_id, None)

            # Finish or pre-gen next
            if next_action == "finish":
                await self.session_repo.update_score(session_id, evaluation_score)
                await self.session_repo.complete_session(
                    session_id=session_id,
                    final_score=evaluation_score,
                    final_feedback=feedback
                )
                logger.info(f"Session {session_id} finalized with score={evaluation_score}")
            else:
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
                "inquisitor_action": "saturate",
                "is_follow_up": is_follow_up,
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
                "rag_context_used": bool(final_state.get("department_requirements")),
                "nodes_executed": final_state.get("nodes_executed", [])
            }

        except Exception as e:
            logger.error(f"Failed to evaluate answer: {e}")
            raise

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
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
        try:
            session_task = self.session_repo.get_session(session_id)
            messages_task = self.message_repo.get_session_messages(session_id)
            session, messages = await asyncio.gather(session_task, messages_task)

            try:
                evaluations = await self.evaluation_repo.get_evaluations_by_session(session_id)
            except Exception:
                evaluations = []

            answered_questions = len([
                m for m in messages
                if m.get("role") == "candidate"
            ])
            total_questions_possible = session.get("total_questions", 10)

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
