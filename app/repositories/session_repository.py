"""
Session repository for managing interview sessions.
"""
import logging
from typing import Optional
from uuid import UUID, uuid4

from app.config.database import get_supabase
from app.exceptions import SessionNotFoundException
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository):
    """
    Repository for interview sessions.
    Handles all database operations for interview_sessions table.
    """
    
    _table_name = "interview_sessions"
    
    def __init__(self):
        """Initialize session repository with database client."""
        db = get_supabase()
        super().__init__(db)
    
    async def create_session(
        self,
        company_id: int,
        job_role: str,
        current_phase: str = "intro",
        candidate_id: Optional[str] = None,
        candidate_name: str = "",
        candidate_email: str = "",
        total_questions: int = 10,
        interview_type: str = "company"
    ) -> dict:
        """
        Create a new interview session.
        """
        session_data = {
            "id": str(uuid4()),
            "company_id": company_id,
            "job_role": job_role,
            "status": "active",
            "current_phase": current_phase,
            "current_question_number": 0,
            "total_questions": total_questions,
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "interview_type": interview_type
        }
        
        return await self.create(session_data, self._table_name)
    
    async def get_session(self, session_id: str) -> dict:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            dict: Session data
            
        Raises:
            SessionNotFoundException: If session not found
            DatabaseException: If retrieval fails
        """
        return await self.get(session_id, self._table_name)
    
    async def update_phase(
        self,
        session_id: str,
        current_phase: str
    ) -> dict:
        """
        Update session phase.
        
        Args:
            session_id: Session ID
            current_phase: New phase
            
        Returns:
            dict: Updated session
            
        Raises:
            SessionNotFoundException: If session not found
            DatabaseException: If update fails
        """
        return await self.update(
            session_id,
            {"current_phase": current_phase},
            self._table_name
        )
    
    async def update_question_number(
        self,
        session_id: str,
        question_number: int
    ) -> dict:
        """
        Update current question number.
        
        Args:
            session_id: Session ID
            question_number: New question number
            
        Returns:
            dict: Updated session
            
        Raises:
            SessionNotFoundException: If session not found
            DatabaseException: If update fails
        """
        return await self.update(
            session_id,
            {"current_question_number": question_number},
            self._table_name
        )
    
    async def update_score(
        self,
        session_id: str,
        final_score: float
    ) -> dict:
        """
        Update final score for session.
        
        Args:
            session_id: Session ID
            final_score: Final score (0-10)
            
        Returns:
            dict: Updated session
            
        Raises:
            SessionNotFoundException: If session not found
            DatabaseException: If update fails
        """
        return await self.update(
            session_id,
            {"final_score": final_score},
            self._table_name
        )
    
    async def update_feedback(
        self,
        session_id: str,
        final_feedback: str
    ) -> dict:
        """
        Update final feedback for session.
        
        Args:
            session_id: Session ID
            final_feedback: Final feedback text
            
        Returns:
            dict: Updated session
            
        Raises:
            SessionNotFoundException: If session not found
            DatabaseException: If update fails
        """
        return await self.update(
            session_id,
            {"final_feedback": final_feedback, "status": "completed"},
            self._table_name
        )
    
    async def complete_session(
        self,
        session_id: str,
        final_score: float,
        final_feedback: str
    ) -> dict:
        """
        Mark session as completed with final score and feedback.
        
        Args:
            session_id: Session ID
            final_score: Final score (0-10)
            final_feedback: Final feedback text
            
        Returns:
            dict: Completed session
        """
        return await self.update(
            session_id,
            {
                "final_score": final_score,
                "final_feedback": final_feedback,
                "status": "completed"
            },
            self._table_name
        )
    
    async def check_completion_before(self, session_id: str) -> tuple[bool, int, Optional[float]]:
        """
        Check if interviews is complete before a certain question.
        
        Args:
            session_id: Session ID
            
        Returns:
            tuple: (is_complete, current_answered_count, total_questions)
        """
        try:
            session = await self.get_session(session_id)
            question_number = session.get("current_question_number", 0)
            total_questions = session.get("total_questions", 10)
            
            # Count messages to see how many have been answered
            messages = await self.list_by_session(
                session_id,
                "interview_messages"
            )
            answered_count = len([m for m in messages if m.get("question_number") < question_number])
            
            is_complete = answered_count >= question_number or question_number >= total_questions
            return is_complete, question_number, total_questions
            
        except Exception as e:
            logger.error(f"Error checking completion: {e}", exc_info=True)
            return False, 0, 0
    
    async def get_session_summary(self, session_id: str) -> dict:
        """
        Get a comprehensive summary of the session.
        
        Args:
            session_id: Session ID
            
        Returns:
            dict: Session summary with messages count, etc.
        """
        try:
            session = await self.get_session(session_id)
            
            # Get messages count
            messages = await self.list_by_session(session_id, "interview_messages")
            questions_attempted = len([
                m for m in messages 
                if m.get("question_number") < session.get("current_question_number", 0)
            ])
            
            return {
                "id": session["id"],
                "company_id": session["company_id"],
                "job_role": session["job_role"],
                "status": session["status"],
                "current_phase": session["current_phase"],
                "current_question_number": session["current_question_number"],
                "total_questions": session["total_questions"],
                "interview_type": session.get("interview_type", "company"),
                "final_score": session.get("final_score"),
                "ended_at": session.get("ended_at"),
                "messages_count": len(messages),
                "questions_attempted": questions_attempted
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}", exc_info=True)
            raise