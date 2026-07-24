import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, and_
from app.models.db import EvidenceStore
from app.exceptions import DatabaseException
from app.repositories.base_repository import BaseRepository
from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


class EvidenceRepository(BaseRepository):
    model_class = EvidenceStore

    def __init__(self):
        super().__init__()

    async def create_evidence(
        self,
        session_id: str,
        competency: str,
        dimension: str,
        score: float,
        evidence_text: str,
        source_question: str,
        question_number: int,
        confidence: float = 1.0,
        hypothesis_id: Optional[str] = None,
        hypothesis_relevance: Optional[float] = None,
        evidence_metadata: Optional[dict] = None,
    ) -> dict:
        from uuid import uuid4
        data = {
            "id": uuid4(),
            "session_id": UUID(session_id),
            "competency": competency,
            "dimension": dimension,
            "score": score,
            "confidence": confidence,
            "evidence_text": evidence_text,
            "source_question": source_question,
            "question_number": question_number,
        }
        if hypothesis_id is not None:
            data["hypothesis_id"] = UUID(hypothesis_id)
        if hypothesis_relevance is not None:
            data["hypothesis_relevance"] = hypothesis_relevance
        if evidence_metadata is not None:
            data["evidence_metadata"] = evidence_metadata
        return await self.create(data, self.model_class)

    async def get_by_session(self, session_id: str) -> list[dict]:
        return await self.list_by_session(session_id, self.model_class, order_by="created_at")

    async def get_by_competency(self, session_id: str, competency: str) -> list[dict]:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(self.model_class)
                    .where(
                        and_(
                            self.model_class.session_id == UUID(session_id),
                            self.model_class.competency == competency,
                        )
                    )
                    .order_by(self.model_class.created_at)
                )
                instances = result.scalars().all()
                return [self._to_dict(inst) for inst in instances]
        except Exception as e:
            logger.error(f"Database error fetching evidence by competency: {e}")
            raise DatabaseException(f"Failed to fetch evidence: {str(e)}")

    async def get_by_dimension(self, session_id: str, dimension: str) -> list[dict]:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(self.model_class)
                    .where(
                        and_(
                            self.model_class.session_id == UUID(session_id),
                            self.model_class.dimension == dimension,
                        )
                    )
                    .order_by(self.model_class.created_at)
                )
                instances = result.scalars().all()
                return [self._to_dict(inst) for inst in instances]
        except Exception as e:
            logger.error(f"Database error fetching evidence by dimension: {e}")
            raise DatabaseException(f"Failed to fetch evidence: {str(e)}")

    async def get_competency_summary(self, session_id: str) -> dict:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                rows = await session.execute(
                    select(
                        self.model_class.competency,
                        func.count(self.model_class.id).label("evidence_count"),
                        func.avg(self.model_class.score).label("average_score"),
                        func.avg(self.model_class.confidence).label("average_confidence"),
                        func.max(self.model_class.created_at).label("last_evidence_at"),
                    )
                    .where(self.model_class.session_id == UUID(session_id))
                    .group_by(self.model_class.competency)
                )
                summary = {}
                for row in rows:
                    summary[row.competency] = {
                        "evidence_count": row.evidence_count,
                        "average_score": round(float(row.average_score), 2) if row.average_score else 0.0,
                        "average_confidence": round(float(row.average_confidence), 2) if row.average_confidence else 0.0,
                        "last_evidence_at": row.last_evidence_at.isoformat() if row.last_evidence_at else None,
                    }
                return summary
        except Exception as e:
            logger.error(f"Database error computing competency summary: {e}")
            raise DatabaseException(f"Failed to compute competency summary: {str(e)}")

    async def get_by_hypothesis(self, hypothesis_id: str) -> list[dict]:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(self.model_class)
                    .where(self.model_class.hypothesis_id == UUID(hypothesis_id))
                    .order_by(self.model_class.created_at)
                )
                instances = result.scalars().all()
                return [self._to_dict(inst) for inst in instances]
        except Exception as e:
            logger.error(f"Database error fetching evidence by hypothesis: {e}")
            raise DatabaseException(f"Failed to fetch evidence: {str(e)}")

    async def get_latest_for_competency(self, session_id: str, competency: str) -> Optional[dict]:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(self.model_class)
                    .where(
                        and_(
                            self.model_class.session_id == UUID(session_id),
                            self.model_class.competency == competency,
                        )
                    )
                    .order_by(self.model_class.created_at.desc())
                    .limit(1)
                )
                instance = result.scalar_one_or_none()
                return self._to_dict(instance) if instance else None
        except Exception as e:
            logger.error(f"Database error fetching latest evidence: {e}")
            return None

    async def delete_by_session(self, session_id: str) -> bool:
        from uuid import UUID
        from sqlalchemy import delete as sa_delete
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
            logger.error(f"Database error deleting evidence: {e}")
            raise DatabaseException(f"Failed to delete evidence: {str(e)}")
