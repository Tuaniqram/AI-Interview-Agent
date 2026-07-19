"""
Evaluation repository for storing structured answer evaluations.
"""
import logging
from typing import Optional

from app.config.database import get_supabase
from app.exceptions import DatabaseException
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class EvaluationRepository(BaseRepository):
    """
    Repository for interview evaluations.
    Handles all database operations for interview_evaluations table.
    Stores structured evaluation data (scores, feedback, strengths, weaknesses).
    """

    _table_name = "interview_evaluations"

    def __init__(self):
        """Initialize evaluation repository with database client."""
        db = get_supabase()
        super().__init__(db)

    async def create_evaluation(
        self,
        session_id: str,
        message_id: str,
        technical_score: float,
        communication_score: float,
        problem_solving_score: Optional[float] = None,
        strengths: Optional[str] = None,
        weaknesses: Optional[str] = None,
        feedback: Optional[str] = None,
        overall_score: Optional[float] = None
    ) -> dict:
        """
        Create a new structured evaluation record.

        Args:
            session_id: Session ID
            message_id: Related message ID (candidate answer)
            technical_score: Technical score (0-10)
            communication_score: Communication score (0-10)
            problem_solving_score: Optional problem-solving score
            strengths: Candidate strengths
            weaknesses: Candidate weaknesses
            feedback: Detailed feedback text
            overall_score: Overall aggregated score

        Returns:
            dict: Created evaluation record
        """
        evaluation_data = {
            "session_id": session_id,
            "message_id": message_id,
            "technical_score": technical_score,
            "communication_score": communication_score,
        }

        if problem_solving_score is not None:
            evaluation_data["problem_solving_score"] = problem_solving_score
        if strengths is not None:
            evaluation_data["strengths"] = strengths
        if weaknesses is not None:
            evaluation_data["weaknesses"] = weaknesses
        if feedback is not None:
            evaluation_data["feedback"] = feedback
        if overall_score is not None:
            evaluation_data["overall_score"] = overall_score

        return await self.create(evaluation_data, self._table_name)

    async def get_evaluations_by_session(
        self,
        session_id: str,
        order_by: str = "created_at"
    ) -> list[dict]:
        """
        Get all evaluations for a session ordered by creation time.

        Args:
            session_id: Session ID
            order_by: Field to order by

        Returns:
            list[dict]: List of evaluation records
        """
        return await self.list_by_session(
            session_id,
            self._table_name,
            order_by=order_by
        )

    async def get_evaluation_by_message(
        self,
        message_id: str
    ) -> Optional[dict]:
        """
        Get the evaluation associated with a specific message.

        Args:
            message_id: Message ID

        Returns:
            dict or None: Evaluation record if found
        """
        try:
            response = (
                self.db.table(self._table_name)
                .select("*")
                .eq("message_id", message_id)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(
                f"Database error fetching evaluation by message: {e}",
                extra={"message_id": message_id}
            )
            raise DatabaseException(f"Failed to fetch evaluation: {str(e)}")
