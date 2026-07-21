"""
Evaluation repository for storing structured answer evaluations using async SQLAlchemy.
"""
import logging
from typing import Optional

from app.models.db import InterviewEvaluation
from app.exceptions import DatabaseException
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class EvaluationRepository(BaseRepository):
    """
    Repository for interview evaluations.
    Uses async SQLAlchemy with InterviewEvaluation ORM model.
    """

    model_class = InterviewEvaluation

    def __init__(self):
        super().__init__()

    async def create_evaluation(
        self,
        session_id: str,
        message_id: str,
        technical_score: float,
        communication_score: float,
        strengths: Optional[str] = None,
        weaknesses: Optional[str] = None,
        feedback: Optional[str] = None,
        overall_score: Optional[float] = None
    ) -> dict:
        from uuid import UUID, uuid4
        evaluation_data = {
            "id": uuid4(),
            "session_id": UUID(session_id),
            "message_id": UUID(message_id),
            "technical_score": technical_score,
            "communication_score": communication_score,
        }
        if strengths is not None:
            evaluation_data["strengths"] = strengths
        if weaknesses is not None:
            evaluation_data["weaknesses"] = weaknesses
        if feedback is not None:
            evaluation_data["feedback_detail"] = feedback
        if overall_score is not None:
            evaluation_data["score"] = overall_score
        return await self.create(evaluation_data, self.model_class)

    async def get_evaluations_by_session(self, session_id: str, order_by: str = "created_at") -> list[dict]:
        return await self.list_by_session(session_id, self.model_class, order_by=order_by)

    async def get_evaluation_by_message(self, message_id: str) -> Optional[dict]:
        from uuid import UUID
        from sqlalchemy import select
        from app.database.session import get_session_factory
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(self.model_class).where(self.model_class.message_id == UUID(message_id)).limit(1)
                )
                instance = result.scalar_one_or_none()
                return self._to_dict(instance) if instance else None
        except Exception as e:
            self.logger.error(f"Database error fetching evaluation by message: {e}")
            raise DatabaseException(f"Failed to fetch evaluation: {str(e)}")
