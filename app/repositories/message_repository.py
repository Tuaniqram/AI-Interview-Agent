"""
Message repository for storing interview question-answer pairs.
"""
import logging
from typing import Optional

from app.config.database import get_supabase
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MessageRepository(BaseRepository):
    """
    Repository for interview messages.
    Handles all database operations for interview_messages table.
    """
    
    _table_name = "interview_messages"
    
    def __init__(self):
        """Initialize message repository with database client."""
        db = get_supabase()
        super().__init__(db)
    
    async def create_message(
        self,
        session_id: str,
        role: str,
        message_type: str,
        content: str,
        question_number: int,
        phase: str,
        score: Optional[float] = None
    ) -> dict:
        """
        Create a new interview message.
        
        Args:
            session_id: Session ID
            role: Role (candidate or interviewer)
            message_type: Message type
            content: Message content
            question_number: Question number
            phase: Interview phase
            score: Optional score (for candidate messages)
            
        Returns:
            dict: Created message
        """
        message_data = {
            "session_id": session_id,
            "role": role,
            "message_type": message_type,
            "content": content,
            "question_number": question_number,
            "phase": phase
        }
        
        if score is not None:
            message_data["score"] = score
        
        return await self.create(message_data, self._table_name)
    
    async def create_candidate_answer(
        self,
        session_id: str,
        role: str,
        candidate_answer: str,
        question_number: int,
        phase: str,
        score: float
    ) -> dict:
        """
        Create a candidate answer message.
        
        Args:
            session_id: Session ID
            role: "candidate"
            candidate_answer: Answer text
            question_number: Question number
            phase: Interview phase
            score: Answer score
            
        Returns:
            dict: Created message
        """
        return await self.create_message(
            session_id=session_id,
            role=role,
            message_type="candidate_answer",
            content=candidate_answer,
            question_number=question_number,
            phase=phase,
            score=score
        )
    
    async def create_question(self, session_id: str, question_text: str, question_number: int, phase: str) -> dict:
        """
        Create a question (interviewer).
        
        Args:
            session_id: Session ID
            question_text: Question text
            question_number: Question number
            phase: Interview phase
            
        Returns:
            dict: Created message
        """
        return await self.create_message(
            session_id=session_id,
            role="interviewer",
            message_type="question",
            content=question_text,
            question_number=question_number,
            phase=phase
        )
    
    async def get_session_messages(
        self,
        session_id: str,
        order_by: str = "created_at"
    ) -> list[dict]:
        """
        Get all messages for a session ordered by creation time.
        
        Args:
            session_id: Session ID
            order_by: Field to order by
            
        Returns:
            list[dict]: List of messages
        """
        return await self.list_by_session(
            session_id,
            self._table_name,
            order_by=order_by
        )
    
    async def get_session_messages_count(
        self,
        session_id: str
    ) -> int:
        """
        Get the count of all messages for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            int: Message count
        """
        messages = await self.get_session_messages(session_id)
        return len(messages)
    
    async def get_messages_before_question(
        self,
        session_id: str,
        question_number: int
    ) -> list[dict]:
        """
        Get messages with question_number less than the specified value.
        
        Args:
            session_id: Session ID
            question_number: Maximum question number
            
        Returns:
            list[dict]: Messages before the specified question
        """
        all_messages = await self.get_session_messages(session_id)
        return [
            m for m in all_messages 
            if m.get("question_number", 0) < question_number
        ]
    
    async def get_legal_candidate_statistics(
        self,
        session_id: str
    ) -> dict:
        """
        Get legal candidate statistics for a session.
        This is for checking which phases have been legally completed based on question count.
        
        Args:
            session_id: Session ID
            
        Returns:
            dict: Statistics showing legal phase completion
        """
        messages = await self.get_session_messages(session_id)
        
        # Group by phase
        phase_counts = {}
        for msg in messages:
            phase = msg.get("phase", "unknown")
            if phase not in phase_counts:
                phase_counts[phase] = 0
            phase_counts[phase] += 1
        
        return {
            "total_messages": len(messages),
            "phase_counts": phase_counts,
            "has_intro": phase_counts.get("intro", 0) >= 2,
            "has_experience": phase_counts.get("experience", 0) >= 3,
            "has_technical": phase_counts.get("technical", 0) >= 5,
            "has_behavioral": phase_counts.get("behavioral", 0) >= 3,
            "has_conclusion": phase_counts.get("conclusion", 0) >= 2  # Usually account for "Do you have questions?"
        }
    
    async def get_evaluations(
        self,
        session_id: str,
        order_by: str = "created_at"
    ) -> list[dict]:
        """
        Get all evaluations for a session.
        Evaluations are stored in interview_messages table with score field.
        
        Args:
            session_id: Session ID
            order_by: Field to order by
            
        Returns:
            list[dict]: List of evaluations with scores
        """
        all_messages = await self.get_session_messages(session_id, order_by=order_by)
        # Filter only messages that have scores (evaluated answers)
        evaluations = [
            m for m in all_messages
            if "score" in m and m["score"] is not None
        ]
        return evaluations
