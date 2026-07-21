"""
Base repository class for database operations.
Provides common patterns for all repository implementations using async SQLAlchemy.
"""
import logging
from typing import Any, Optional
from sqlalchemy import select, update, delete as sa_delete, func
from app.database.session import get_session_factory
from app.exceptions import RecordNotFoundException, DatabaseException

logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Base repository with async SQLAlchemy helpers.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def _get_session(self):
        if get_session_factory() is None:
            raise RuntimeError("DATABASE_URL not configured")
        async with get_session_factory()() as session:
            yield session

    async def get(self, id: str, model_class) -> dict:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(model_class).where(model_class.id == UUID(id))
                )
                instance = result.scalar_one_or_none()
                if instance is None:
                    raise RecordNotFoundException(table=model_class.__tablename__, identifier="id", value=id)
                return self._to_dict(instance)
        except RecordNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Database error: {e}")
            raise DatabaseException(f"Failed to get record: {str(e)}")

    async def create(self, data: dict, model_class) -> dict:
        try:
            async with get_session_factory()() as session:
                instance = model_class(**data)
                session.add(instance)
                await session.commit()
                await session.refresh(instance)
                return self._to_dict(instance)
        except Exception as e:
            self.logger.error(f"Database error creating record: {e}")
            raise DatabaseException(f"Failed to create record: {str(e)}")

    async def update(self, id: str, updates: dict, model_class) -> dict:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(model_class).where(model_class.id == UUID(id))
                )
                instance = result.scalar_one_or_none()
                if instance is None:
                    raise RecordNotFoundException(table=model_class.__tablename__, identifier="id", value=id)
                for key, value in updates.items():
                    setattr(instance, key, value)
                await session.commit()
                await session.refresh(instance)
                return self._to_dict(instance)
        except RecordNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Database error updating record: {e}")
            raise DatabaseException(f"Failed to update record: {str(e)}")

    async def delete(self, id: str, model_class) -> bool:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(model_class).where(model_class.id == UUID(id))
                )
                instance = result.scalar_one_or_none()
                if instance is None:
                    return False
                await session.delete(instance)
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"Database error deleting record: {e}")
            raise DatabaseException(f"Failed to delete record: {str(e)}")

    async def list_by_session(self, session_id: str, model_class, order_by: Optional[str] = None) -> list[dict]:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                query = select(model_class).where(model_class.session_id == UUID(session_id))
                if order_by:
                    order_col = getattr(model_class, order_by, None)
                    if order_col is not None:
                        query = query.order_by(order_col)
                result = await session.execute(query)
                instances = result.scalars().all()
                return [self._to_dict(inst) for inst in instances]
        except Exception as e:
            self.logger.error(f"Database error listing records: {e}")
            raise DatabaseException(f"Failed to list records: {str(e)}")

    async def exists(self, id: str, model_class) -> bool:
        from uuid import UUID
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(model_class.id).where(model_class.id == UUID(id)).limit(1)
                )
                return result.scalar_one_or_none() is not None
        except Exception as e:
            self.logger.error(f"Database error checking existence: {e}")
            raise DatabaseException(f"Failed to check existence: {str(e)}")

    def _to_dict(self, instance) -> dict:
        """Convert SQLAlchemy model instance to dict, handling UUID and datetime."""
        result = {}
        for column in instance.__table__.columns:
            value = getattr(instance, column.name)
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            elif hasattr(value, 'hex'):
                value = str(value)
            result[column.name] = value
        return result
