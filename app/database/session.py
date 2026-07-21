"""
Async SQLAlchemy engine and session factory.
DATABASE_URL must be set in .env for SQLAlchemy/Alembic to connect.
The URL scheme is auto-upgraded to asyncpg if needed.
Engine is created lazily to avoid event-loop binding issues in testing.
"""
import os
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

# Auto-upgrade sync postgresql:// to async postgresql+asyncpg://
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

_engine = None
_async_session_factory = None


def get_engine():
    """Get or create the async engine lazily (one per process)."""
    global _engine
    if _engine is None and DATABASE_URL:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=10,
            max_overflow=20,
            connect_args={"statement_cache_size": 0},
        )
        logger.info("Async SQLAlchemy engine created")
    return _engine


def get_session_factory():
    """Get or create the async session factory lazily."""
    global _async_session_factory
    if _async_session_factory is None:
        eng = get_engine()
        if eng:
            _async_session_factory = async_sessionmaker(
                eng,
                class_=AsyncSession,
                expire_on_commit=False,
            )
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError(
            "DATABASE_URL not configured — cannot create async sessions"
        )
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
