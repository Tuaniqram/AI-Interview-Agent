"""
Repository factory for accessing repositories.
Provides a clean way to get repository instances.
"""
from app.repositories.session_repository import SessionRepository
from app.repositories.message_repository import MessageRepository


class Repositories:
    """Factory class for repository access."""
    
    _session_repository: SessionRepository = None
    _message_repository: MessageRepository = None
    
    @classmethod
    def get_session_repository(cls) -> SessionRepository:
        """Get or create session repository."""
        if cls._session_repository is None:
            cls._session_repository = SessionRepository()
        return cls._session_repository
    
    @classmethod
    def get_message_repository(cls) -> MessageRepository:
        """Get or create message repository."""
        if cls._message_repository is None:
            cls._message_repository = MessageRepository()
        return cls._message_repository


# Convenience functions for quick access
def get_session_repo() -> SessionRepository:
    """Get session repository instance."""
    return Repositories.get_session_repository()


def get_message_repo() -> MessageRepository:
    """Get message repository instance."""
    return Repositories.get_message_repository()