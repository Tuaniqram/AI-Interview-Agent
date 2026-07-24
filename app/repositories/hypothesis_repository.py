import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update as sa_update, and_
from app.models.db import Hypothesis
from app.exceptions import DatabaseException
from app.repositories.base_repository import BaseRepository
from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


class HypothesisRepository(BaseRepository):
    model_class = Hypothesis

    def __init__(self):
        super().__init__()

    async def create_hypothesis(
        self,
        session_id: str,
        statement: str,
        direction: str,
        confidence: float = 0.0,
        status: str = "untested",
    ) -> dict:
        from uuid import uuid4
        data = {
            "id": uuid4(),
            "session_id": UUID(session_id),
            "statement": statement,
            "direction": direction,
            "confidence": confidence,
            "status": status,
            "supporting_evidence": [],
            "contradicting_evidence": [],
        }
        return await self.create(data, self.model_class)

    async def get_by_session(self, session_id: str) -> list[dict]:
        return await self.list_by_session(session_id, self.model_class, order_by="created_at")

    async def get_active_by_session(self, session_id: str) -> list[dict]:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(self.model_class)
                    .where(
                        and_(
                            self.model_class.session_id == UUID(session_id),
                            self.model_class.status.in_(["untested", "testing"]),
                        )
                    )
                    .order_by(self.model_class.created_at)
                )
                instances = result.scalars().all()
                return [self._to_dict(inst) for inst in instances]
        except Exception as e:
            logger.error(f"Database error fetching active hypotheses: {e}")
            raise DatabaseException(f"Failed to fetch hypotheses: {str(e)}")

    async def update_confidence(
        self,
        hypothesis_id: str,
        confidence: float,
        status: str,
        evidence_id: str,
        supports: bool,
    ) -> dict:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(self.model_class).where(self.model_class.id == UUID(hypothesis_id))
                )
                instance = result.scalar_one_or_none()
                if instance is None:
                    raise DatabaseException(f"Hypothesis not found: {hypothesis_id}")
                instance.confidence = confidence
                instance.status = status
                if supports:
                    instance.supporting_evidence = (instance.supporting_evidence or []) + [UUID(evidence_id)]
                else:
                    instance.contradicting_evidence = (instance.contradicting_evidence or []) + [UUID(evidence_id)]
                await session.commit()
                await session.refresh(instance)
                return self._to_dict(instance)
        except Exception as e:
            logger.error(f"Database error updating hypothesis confidence: {e}")
            raise DatabaseException(f"Failed to update hypothesis: {str(e)}")

    async def bulk_create(self, hypotheses: list[dict]) -> list[dict]:
        from uuid import uuid4
        try:
            async with get_session_factory()() as session:
                instances = []
                for h in hypotheses:
                    instance = self.model_class(
                        id=uuid4(),
                        session_id=UUID(h["session_id"]),
                        statement=h["statement"],
                        direction=h["direction"],
                        confidence=h.get("confidence", 0.0),
                        status=h.get("status", "untested"),
                        supporting_evidence=[],
                        contradicting_evidence=[],
                    )
                    session.add(instance)
                    instances.append(instance)
                await session.commit()
                for inst in instances:
                    await session.refresh(inst)
                return [self._to_dict(inst) for inst in instances]
        except Exception as e:
            logger.error(f"Database error bulk creating hypotheses: {e}")
            raise DatabaseException(f"Failed to create hypotheses: {str(e)}")

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
            logger.error(f"Database error deleting hypotheses: {e}")
            raise DatabaseException(f"Failed to delete hypotheses: {str(e)}")
