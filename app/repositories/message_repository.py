"""
Message repository for interview messages using async SQLAlchemy.
"""
import logging
from typing import Optional

from app.models.db import InterviewMessage
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MessageRepository(BaseRepository):
    """
    Repository for interview messages.
    Uses async SQLAlchemy with InterviewMessage ORM model.
    """

    model_class = InterviewMessage

    def __init__(self):
        super().__init__()

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
        from uuid import UUID, uuid4
        message_data = {
            "id": uuid4(),
            "session_id": UUID(session_id),
            "role": role,
            "message_type": message_type,
            "content": content,
            "question_number": question_number,
            "phase": phase,
        }
        if score is not None:
            message_data["score"] = score
        return await self.create(message_data, self.model_class)

    async def create_candidate_answer(
        self, session_id: str, role: str, candidate_answer: str,
        question_number: int, phase: str, score: float
    ) -> dict:
        return await self.create_message(
            session_id=session_id, role=role, message_type="candidate_answer",
            content=candidate_answer, question_number=question_number,
            phase=phase, score=score
        )

    async def create_question(self, session_id: str, question_text: str, question_number: int, phase: str) -> dict:
        return await self.create_message(
            session_id=session_id, role="interviewer", message_type="question",
            content=question_text, question_number=question_number, phase=phase
        )

    async def get_session_messages(self, session_id: str, order_by: str = "created_at") -> list[dict]:
        return await self.list_by_session(session_id, self.model_class, order_by=order_by)

    async def get_session_messages_count(self, session_id: str) -> int:
        messages = await self.get_session_messages(session_id)
        return len(messages)

    async def get_messages_before_question(self, session_id: str, question_number: int) -> list[dict]:
        from uuid import UUID
        from sqlalchemy import select
        from app.database.session import get_session_factory
        try:
            async with get_session_factory()() as session:
                query = (
                    select(self.model_class)
                    .where(self.model_class.session_id == UUID(session_id))
                    .where(self.model_class.question_number < question_number)
                    .order_by(self.model_class.created_at)
                )
                result = await session.execute(query)
                instances = result.scalars().all()
                return [self._to_dict(inst) for inst in instances]
        except Exception as e:
            self.logger.error(f"Database error listing messages before question: {e}")
            raise

    async def get_legal_candidate_statistics(self, session_id: str) -> dict:
        messages = await self.get_session_messages(session_id)
        phase_counts = {}
        for msg in messages:
            phase = msg.get("phase", "unknown")
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        return {
            "total_messages": len(messages),
            "phase_counts": phase_counts,
            "has_intro": phase_counts.get("intro", 0) >= 2,
            "has_experience": phase_counts.get("experience", 0) >= 3,
            "has_technical": phase_counts.get("technical", 0) >= 5,
            "has_behavioral": phase_counts.get("behavioral", 0) >= 3,
            "has_conclusion": phase_counts.get("conclusion", 0) >= 2,
        }

    async def get_evaluations(self, session_id: str, order_by: str = "created_at") -> list[dict]:
        all_messages = await self.get_session_messages(session_id, order_by=order_by)
        return [m for m in all_messages if "score" in m and m["score"] is not None]
