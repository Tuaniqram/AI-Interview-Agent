"""
Session repository for interview sessions using async SQLAlchemy.
"""
import logging
from typing import Optional
from uuid import uuid4

from app.models.db import InterviewSession, InterviewMessage
from app.exceptions import SessionNotFoundException, RecordNotFoundException
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository):
    """
    Repository for interview sessions.
    Uses async SQLAlchemy with InterviewSession ORM model.
    """

    model_class = InterviewSession

    def __init__(self):
        super().__init__()

async def create_session(
    self,
    department_id: Optional[int] = None,
    job_role: str = "",
    current_phase: str = "intro",
    total_questions: int = 10,
    session_type: str = "department",
    interaction_mode: str = "avatar",
    candidate_profile_id: Optional[str] = None,
) -> dict:
    session_data = {
        "id": uuid4(),
        "department_id": department_id,
        "job_role": job_role,
        "status": "active",
        "current_phase": current_phase,
        "current_question_number": 1,
        "total_questions": total_questions,
        "session_type": session_type,
        "interaction_mode": interaction_mode,
    }
    if candidate_profile_id is not None:
        session_data["candidate_profile_id"] = candidate_profile_id
    return await self.create(session_data, self.model_class)

    async def get_session(self, session_id: str) -> dict:
        try:
            return await self.get(session_id, self.model_class)
        except RecordNotFoundException:
            raise SessionNotFoundException(session_id)

    async def update_phase(self, session_id: str, current_phase: str) -> dict:
        return await self.update(session_id, {"current_phase": current_phase}, self.model_class)

    async def update_question_number(self, session_id: str, question_number: int) -> dict:
        return await self.update(session_id, {"current_question_number": question_number}, self.model_class)

    async def update_score(self, session_id: str, final_score: float) -> dict:
        return await self.update(session_id, {"final_score": final_score}, self.model_class)

    async def update_feedback(self, session_id: str, final_feedback: str) -> dict:
        return await self.update(
            session_id,
            {"final_feedback": final_feedback, "status": "completed"},
            self.model_class
        )

    async def complete_session(self, session_id: str, final_score: float, final_feedback: str) -> dict:
        return await self.update(
            session_id,
            {"final_score": final_score, "final_feedback": final_feedback, "status": "completed"},
            self.model_class
        )

    async def check_completion_before(self, session_id: str) -> tuple[bool, int, Optional[float]]:
        try:
            session = await self.get_session(session_id)
            question_number = session.get("current_question_number", 0)
            total_questions = session.get("total_questions", 10)
            total_messages = await self._count_messages_for_session(session_id)
            answered_count = total_messages
            is_complete = answered_count >= question_number or question_number >= total_questions
            return is_complete, question_number, total_questions
        except Exception as e:
            logger.error(f"Error checking completion: {e}", exc_info=True)
            return False, 0, 0

    async def _count_messages_for_session(self, session_id: str) -> int:
        from uuid import UUID
        from sqlalchemy import select, func
        from app.database.session import get_session_factory
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(func.count()).where(InterviewMessage.session_id == UUID(session_id))
                )
                return result.scalar() or 0
        except Exception as e:
            self.logger.error(f"Error counting messages: {e}")
            return 0

    async def get_session_summary(self, session_id: str) -> dict:
        try:
            session = await self.get_session(session_id)
            messages = await self.list_by_session(session_id, InterviewMessage)
            questions_attempted = len([
                m for m in messages
                if m.get("question_number", 0) < session.get("current_question_number", 0)
            ])
            return {
                "id": session["id"],
                "department_id": session["department_id"],
                "job_role": session["job_role"],
                "status": session["status"],
                "current_phase": session["current_phase"],
                "current_question_number": session["current_question_number"],
                "total_questions": session["total_questions"],
                "session_type": session.get("session_type", "company"),
                "final_score": session.get("final_score"),
                "ended_at": session.get("ended_at"),
                "messages_count": len(messages),
                "questions_attempted": questions_attempted
            }
        except Exception as e:
            logger.error(f"Error getting session summary: {e}", exc_info=True)
            raise
