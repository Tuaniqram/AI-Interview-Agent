import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, and_
from app.models.db import Observation
from app.exceptions import DatabaseException
from app.repositories.base_repository import BaseRepository
from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


class ObservationRepository(BaseRepository):
    model_class = Observation

    def __init__(self):
        super().__init__()

    async def create_observation(
        self,
        session_id: str,
        question_number: int,
        type: str,
        value: float,
        evidence: str,
        pattern: Optional[str] = None,
        risk_signal: Optional[dict] = None,
    ) -> dict:
        from uuid import uuid4
        data = {
            "id": uuid4(),
            "session_id": UUID(session_id),
            "question_number": question_number,
            "type": type,
            "value": value,
            "evidence": evidence,
        }
        if pattern is not None:
            data["pattern"] = pattern
        if risk_signal is not None:
            data["risk_signal"] = risk_signal
        return await self.create(data, self.model_class)

    async def get_by_session(self, session_id: str) -> list[dict]:
        return await self.list_by_session(session_id, self.model_class, order_by="created_at")

    async def get_by_type(self, session_id: str, type: str) -> list[dict]:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(self.model_class)
                    .where(
                        and_(
                            self.model_class.session_id == UUID(session_id),
                            self.model_class.type == type,
                        )
                    )
                    .order_by(self.model_class.created_at)
                )
                instances = result.scalars().all()
                return [self._to_dict(inst) for inst in instances]
        except Exception as e:
            logger.error(f"Database error fetching observations by type: {e}")
            raise DatabaseException(f"Failed to fetch observations: {str(e)}")

    async def get_trends(self, session_id: str) -> dict:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                rows = await session.execute(
                    select(
                        self.model_class.type,
                        func.avg(self.model_class.value).label("avg_value"),
                        func.count(self.model_class.id).label("count"),
                    )
                    .where(self.model_class.session_id == UUID(session_id))
                    .group_by(self.model_class.type)
                )
                trends = {}
                for row in rows:
                    trends[row.type] = {
                        "average_value": round(float(row.avg_value), 2) if row.avg_value else 0.0,
                        "count": row.count,
                    }
                return trends
        except Exception as e:
            logger.error(f"Database error computing observation trends: {e}")
            return {}

    async def get_risk_signals(self, session_id: str) -> list[dict]:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(self.model_class)
                    .where(
                        and_(
                            self.model_class.session_id == UUID(session_id),
                            self.model_class.risk_signal.isnot(None),
                        )
                    )
                    .order_by(self.model_class.created_at)
                )
                instances = result.scalars().all()
                return [self._to_dict(inst) for inst in instances]
        except Exception as e:
            logger.error(f"Database error fetching risk signals: {e}")
            return []

    async def delete_by_session(self, session_id: str) -> bool:
        from sqlalchemy import delete as sa_delete
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                await session.execute(
                    sa_delete(self.model_class).where(
                        self.model_class.session_id == UUID(session_id)
                    )
                )
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Database error deleting observations: {e}")
            raise DatabaseException(f"Failed to delete observations: {str(e)}")
