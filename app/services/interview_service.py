"""
Interview Service - Core business logic for interview management.
Handles interview workflows, LLM operations, and orchestration.
"""
import logging
from typing import Optional

from app.services.llm_service import get_llm_service
from app.services.prompt_loader import load_prompt
from app.services.repositories import get_session_repo, get_message_repo
from app.exceptions import SessionNotFoundException, LLMServiceError

logger = logging.getLogger(__name__)


class InterviewService:
    """
    Service layer for interview management.
    Contains business logic for interview workflows.
    """
    
    def __init__(self):
        """Initialize interview service."""
        self.llm_service = get_llm_service()
        self.session_repo = get_session_repo()
        self.message_repo = get_message_repo()
    
    async def start_interview(
        self,
        company_id: int,
        job_role: str,
        current_phase: str = "intro"
    ) -> dict:
        """
        Start a new interview session.
        
        Args:
            company_id: Company ID
            job_role: Job role for the interview
            current_phase: Current phase (default: "intro")
            
        Returns:
            dict: Created session with session_id, current_phase, question_number, total_questions
        """
        session = await self.session_repo.create_session(
            company_id=company_id,
            job_role=job_role,
            current_phase=current_phase
        )
        
        logger.info(
            f"Started interview for company {company_id}, "
            f"job_role {job_role}, "
            f"session {session['id']}"
        )
        
        return {
            "session_id": session["id"],
            "current_phase": session["current_phase"],
            "question_number": session["current_question_number"],
            "total_questions": session["total_questions"]
        }
    
    async def get_session(self, session_id: str) -> dict:
        """
        Get session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            dict: Session data
            
        Raises:
            SessionNotFoundException: If session not found
        """
        return await self.session_repo.get_session(session_id)
    
    async def get_session_summary(self, session_id: str) -> dict:
        """
        Get comprehensive session summary including messages and evaluations.
        
        Args:
            session_id: Session ID
            
        Returns:
            dict: Complete session summary with metrics
            
        Raises:
            SessionNotFoundException: If session not found
        """
        # Get session
        session = await self.session_repo.get_session(session_id)
        
        # Get messages
        messages = await self.message_repo.get_session_messages(session_id)
        
        # Get evaluations (filter by session_id and extract relevant data)
        evaluations = await self.message_repo.get_evaluations(session_id)
        
        # Calculate metrics
        total_questions_answered = len([m for m in messages if m.get("question_number") < session.get("current_question_number", 0)])
        total_questions_possible = session.get("total_questions", 10)
        
        # Calculate final score
        final_score = session.get("final_score")
        if not final_score:
            # Calculate from evaluations if session is not completed
            scores = [float(e.get("score", 0)) for e in evaluations]
            if scores:
                final_score = sum(scores) / len(scores)
        
        # Calculate metrics
        answered_ratio = total_questions_answered / total_questions_possible if total_questions_possible > 0 else 0
        
        return {
            "session_id": session_id,
            "company_id": session["company_id"],
            "job_role": session["job_role"],
            "status": session["status"],
            "current_phase": session["current_phase"],
            "question_number": session["current_question_number"],
            "total_questions": session["total_questions"],
            "final_score": round(final_score, 2) if final_score else None,
            "answered_ratio": round(answered_ratio, 2),
            "total_questions_answered": total_questions_answered,
            "total_questions_possible": total_questions_possible,
            "messages_count": len(messages),
            "evaluations_count": len(evaluations),
            "interview_complete": session["status"] == "completed" or total_questions_answered >= total_questions_possible,
            "messages": messages,
            "evaluations": evaluations
        }
    
    async def generate_next_question(
        self,
        company_id: int,
        session_id: str,
        job_role: str,
        conversation_history: str,
        current_phase: str,
        question_number: int,
        difficulty_level: int = 1,
        previous_scores: Optional[list] = None
    ) -> dict:
        """
        Generate the next interview question based on phase, history, and performance.
        
        Args:
            company_id: Company ID
            session_id: Session ID
            job_role: Job role
            conversation_history: Previous conversation history
            current_phase: Current interview phase
            question_number: Current question number
            difficulty_level: Difficulty level (1, 2, or 3)
            previous_scores: List of previous scores
            
        Returns:
            dict: Question, phase, question_number, difficulty_level, status
            
        Raises:
            SessionNotFoundException: If session not found
        """
        # Get session to determine total questions
        session = await self.session_repo.get_session(session_id)
        total_questions = session.get("total_questions", 10)
        
        # Determine difficulty based on performance
        adjusted_difficulty = difficulty_level
        if current_phase == "technical" and previous_scores:
            avg_score = sum(previous_scores) / len(previous_scores) if previous_scores else 0
            
            if avg_score > 7.0:  # Strong performance
                adjusted_difficulty = 3
            elif avg_score < 5.0:  # Weak performance
                adjusted_difficulty = 1
            else:  # Average
                adjusted_difficulty = 2
        
        # Generate question text
        question_text = await self._generate_phase_question(
            company_id=company_id,
            job_role=job_role,
            phase=current_phase,
            difficulty_level=adjusted_difficulty,
            conversation_history=conversation_history,
            question_number=question_number
        )
        
        # Update question number
        await self.session_repo.update_question_number(
            session_id=session_id,
            question_number=question_number + 1
        )
        
        # Phase transitions handled by decision_node in LangGraph workflow
        next_phase = current_phase
        next_status = "in_progress"
        
        logger.info(
            f"Generated question {question_number + 1} in phase {current_phase} "
            f"(difficulty {adjusted_difficulty})"
        )
        
        return {
            "question": question_text,
            "phase": current_phase,
            "question_number": question_number,
            "difficulty_level": adjusted_difficulty,
            "interview_status": next_status,
            "total_questions": total_questions  # Always include total_questions
        }
    
    async def evaluate_answer(
        self,
        company_id: int,
        session_id: str,
        job_role: str,
        question: str,
        candidate_answer: str,
        current_phase: str,
        difficulty_level: int
    ) -> dict:
        """
        Evaluate candidate answer and generate suggestions.
        
        Args:
            company_id: Company ID
            session_id: Session ID
            job_role: Job role
            question: Question asked
            candidate_answer: Candidate's answer
            current_phase: Current interview phase
            difficulty_level: Question difficulty
            
        Returns:
            dict: Evaluation results with score, feedback, follow-up
            
        Raises:
            SessionNotFoundException: If session not found
        """
        # Load evaluation prompt
        prompt = load_prompt(
            "evaluation",
            "answer_evaluation.md",
            job_role=job_role,
            question=question,
            candidate_answer=candidate_answer,
            phase=current_phase,
            difficulty_level=difficulty_level
        )
        
        # Get evaluation from LLM (1024 tokens - needs room for detailed feedback)
        evaluation_text = await self.llm_service.invoke(
            prompt=prompt,
            temperature=0.3,  # Low temperature for consistency
            max_tokens=1024  # Room for detailed score, feedback, and follow-up
        )
        
        # Parse evaluation results
        result = self._parse_evaluation(evaluation_text)
        
        # Store message
        await self.message_repo.create_candidate_answer(
            session_id=session_id,
            role="candidate",
            candidate_answer=candidate_answer,
            question_number=0,  # Will be updated later
            phase=current_phase,
            score=result["score"]
        )
        
        logger.info(f"Evaluated answer for session {session_id}: score {result['score']}")
        
        return result
    
    async def handle_answer_submit(
        self,
        company_id: int,
        session_id: str,
        job_role: str,
        question: str,
        candidate_answer: str,
        conversation_history: str,
        current_phase: str,
        difficulty_level: int,
        question_number: int
    ) -> dict:
        """
        Handle full answer submission: evaluate, update state, generate follow-up.
        
        Args:
            company_id: Company ID
            session_id: Session ID
            job_role: Job role
            question: Question asked
            candidate_answer: Candidate's answer
            conversation_history: Conversation history
            current_phase: Current phase
            difficulty_level: Difficulty level
            question_number: Current question number
            
        Returns:
            dict: Evaluation, suggested follow-up, updated phase, status
        """
        # Evaluate answer
        evaluation = await self.evaluate_answer(
            company_id=company_id,
            session_id=session_id,
            job_role=job_role,
            question=question,
            candidate_answer=candidate_answer,
            current_phase=current_phase,
            difficulty_level=difficulty_level
        )
        
        # Update message number
        await self.message_repo.create_candidate_answer(
            session_id=session_id,
            role="candidate",
            candidate_answer=candidate_answer,
            question_number=question_number,
            phase=current_phase,
            score=evaluation["score"]
        )
        
        # Adapt to performance and determine next state
        next_phase, next_difficulty, next_status = await self._adapt_to_performance(
            current_phase=current_phase,
            question_number=question_number,
            score=evaluation["score"],
            session_id=session_id
        )
        
        # Check if interview is complete
        if next_status == "completed":
            # Get session for total questions
            session = await self.session_repo.get_session(session_id)
            total_q = session.get("total_questions", 10)
            # Calculate final score
            final_score = self._calculate_final_score(
                score=evaluation["score"],
                question_number=question_number,
                total_questions=total_q,
                next_difficulty=next_difficulty
            )
            
            # Complete session
            await self.session_repo.complete_session(
                session_id=session_id,
                final_score=final_score,
                final_feedback=evaluation["feedback_detail"]
            )
        else:
            # Update session state
            await self.session_repo.update_phase(
                session_id=session_id,
                current_phase=next_phase
            )
        
        return {
            "evaluation": evaluation.get("feedback_detail", ""),
            "suggested_follow_up": evaluation.get("suggested_follow_up", ""),
            "phase": next_phase,
            "question_number": question_number,
            "difficulty_level": next_difficulty,
            "interview_status": next_status,
            "score": evaluation["score"]
        }
    
    async def _generate_phase_question(
        self,
        company_id: int,
        job_role: str,
        phase: str,
        difficulty_level: int,
        conversation_history: str,
        question_number: int
    ) -> str:
        """
        Generate phase-appropriate question using LLM.
        
        Args:
            company_id: Company ID
            job_role: Job role
            phase: Interview phase
            difficulty_level: Difficulty level
            conversation_history: Conversation history
            question_number: Question number
            
        Returns:
            str: Generated question
        """
        # Check if we have template questions for this phase
        templates = self._get_phase_templates()
        
        if question_number < len(templates.get(phase, [])):
            return templates[phase][question_number]
        
        # Generate AI question
        try:
            # Debug: Check what parameters are being passed
            logger.debug(f"Generating question with params:")
            logger.debug(f"  job_role: {job_role}")
            logger.debug(f"  phase: {phase}")
            logger.debug(f"  difficulty_level: {difficulty_level}")
            logger.debug(f"  previous_context length: {len(conversation_history)}")
            
            prompt = load_prompt(
                "interview",
                "question_generation.md",
                job_role=job_role,
                phase=phase,
                difficulty_level=difficulty_level,
                previous_context=conversation_history
            )
            
            # Debug: Log first few hundred chars of prompt to verify substitution
            logger.debug(f"Prompt first 500 chars:\n{prompt[:500]}")
            
            question = await self.llm_service.invoke(
                prompt=prompt,
                temperature=0.7,
                max_tokens=512  # Single question doesn't need much output
            )
            
            return question
            
        except (FileNotFoundError, LLMServiceError) as e:
            logger.error(f"Failed to generate AI question: {e}")
            # Fall back to generic question
            return f"Can you tell me more about your experience with {job_role}?"
    
    async def _adapt_to_performance(
        self,
        current_phase: str,
        question_number: int,
        score: float,
        session_id: str
    ) -> tuple[str, int, str]:
        """
        Adapt phase, difficulty, and status based on performance.
        
        Args:
            current_phase: Current phase
            question_number: Question number
            score: Candidate's answer score
            session_id: Session ID
            
        Returns:
            tuple[str, int, str]: (next_phase, next_difficulty, next_status)
        """
        next_phase = current_phase
        next_difficulty = 1
        next_status = "in_progress"
        
        # Adapt difficulty based on score
        if score > 7.0:
            next_difficulty = 3
        elif score > 5.0:
            next_difficulty = 2
        
        # Phase transitions
        if current_phase == "intro" and question_number >= 2:
            next_phase = "experience"
        
        elif current_phase == "experience" and question_number >= 5:
            next_phase = "technical"
        
        elif current_phase == "technical" and score < 5.0:
            next_phase = "technical"  # Stay in technical phase
        elif current_phase == "technical" and score > 7.0 and question_number >= 10:
            next_phase = "behavioral"
        
        elif current_phase == "behavioral" and question_number >= 13:
            next_phase = "conclusion"
        
        elif current_phase == "conclusion":
            next_status = "completed"
        
        return next_phase, next_difficulty, next_status
    
    def _parse_evaluation(self, evaluation_text: str) -> dict:
        """
        Parse evaluation text from LLM response.
        
        Args:
            evaluation_text: Full evaluation text
            
        Returns:
            dict: Parsed evaluation data
        """
        try:
            # Try to parse JSON first
            if '```json' in evaluation_text:
                json_str = evaluation_text.split('```json')[1].split('```')[0].strip()
                import json
                return json.loads(json_str)
            elif '```' in evaluation_text:
                json_str = evaluation_text.split('```')[1].split('```')[0].strip()
                import json
                return json.loads(json_str)
        except:
            pass
        
        # Fallback parsing (as in original code)
        score = 7
        strengths = []
        weaknesses = []
        suggested_follow_up = ""
        
        for line in evaluation_text.split('\n'):
            line = line.strip()
            if line.startswith("**Score:"):
                for word in line.split():
                    try:
                        score = float(word.replace("/", "").replace(":", "").strip())
                        break
                    except:
                        pass
            elif line.startswith("**Strengths"):
                for following_line in evaluation_text.split('\n'):
                    l = following_line.strip()
                    if l and not l.startswith("**"):
                        strengths.append(l)
                    elif l.startswith("**"):
                        break
            elif line.startswith("**Areas for Growth"):
                for following_line in evaluation_text.split('\n'):
                    l = following_line.strip()
                    if l and not l.startswith("**"):
                        weaknesses.append(l)
                    elif l.startswith("**"):
                        break
            elif "Suggested Follow-up" in line:
                continue
            elif suggested_follow_up == "":
                suggested_follow_up = (
                    line
                    .replace(">", "")
                    .replace('"', "")
                    .strip()
                )
        
        return {
            "score": score,
            "strengths": ", ".join(strengths[-5:]) if strengths else "None identified",
            "weaknesses": ", ".join(weaknesses[-5:]) if weaknesses else "None identified",
            "feedback_detail": evaluation_text,
            "suggested_follow_up": suggested_follow_up
        }
    
    def _calculate_final_score(
        self,
        score: float,
        question_number: int,
        total_questions: int,
        next_difficulty: int
    ) -> float:
        """
        Calculate final interview score.
        
        Args:
            score: Last question score
            question_number: Number of questions answered
            total_questions: Total questions available
            next_difficulty: Final difficulty level
            
        Returns:
            float: Final score (0-10)
        """
        # Weighted calculation
        base_score = score * 5.0  # Convert 0-2 scale to 0-10
        difficulty_bonus = next_difficulty * 0.5
        progress_factor = (question_number / total_questions) * 2.0
        
        final_score = base_score + difficulty_bonus + progress_factor
        return min(10.0, max(0.0, final_score))
    
    def _get_phase_templates(self) -> dict:
        """
        Get question templates for each phase.
        
        Returns:
            dict: Phase name -> list of questions
        """
        return {
            "intro": [
                "Tell me about yourself and your career background.",
                "What interests you about this role and our company?"
            ],
            "experience": [
                "Can you walk me through your most complex project?",
                "What were your key responsibilities in that role?",
                "What technologies did you use and why?"
            ],
            "technical": [
                "How would you design a scalable API for our use case?",
                "Tell me about a performance bottleneck you faced and how you solved it.",
                "How do you handle data validation and security considerations?",
                "Can you explain your approach to database optimization?",
                "Walk me through your CI/CD pipeline."
            ],
            "behavioral": [
                "Tell me about a time you failed and what you learned.",
                "Describe a conflict with a teammate and how you resolved it.",
                "How do you handle tight deadlines and pressure?"
            ],
            "conclusion": [
                "Do you have any questions for us?",
                "Is there anything else you would like to add about your qualifications?",
                "What are you looking for in your next role?"
            ]
        }