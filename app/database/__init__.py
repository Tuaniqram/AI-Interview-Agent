"""
Async SQLAlchemy database layer.
Provides engine, session factory, and FastAPI dependency.

Import directly for type hints:
    from app.database.base import Base
    from app.database.session import get_db
"""
from app.database.base import Base

__all__ = ["Base"]
