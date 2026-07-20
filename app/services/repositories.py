"""
Repository factory for accessing repositories.
Provides a clean way to get repository instances.
"""
from app.repositories.session_repository import SessionRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.evaluation_repository import EvaluationRepository


class Repositories:
    """Factory class for repository access."""
    
    _session_repository: SessionRepository = None
    _message_repository: MessageRepository = None
    _evaluation_repository: EvaluationRepository = None
    
    @classmethod
    def get_session_repository(cls) -> SessionRepository:
        if cls._session_repository is None:
            cls._session_repository = SessionRepository()
        return cls._session_repository
    
    @classmethod
    def get_message_repository(cls) -> MessageRepository:
        if cls._message_repository is None:
            cls._message_repository = MessageRepository()
        return cls._message_repository
    
    @classmethod
    def get_evaluation_repository(cls) -> EvaluationRepository:
        if cls._evaluation_repository is None:
            cls._evaluation_repository = EvaluationRepository()
        return cls._evaluation_repository


def get_session_repo() -> SessionRepository:
    return Repositories.get_session_repository()


def get_message_repo() -> MessageRepository:
    return Repositories.get_message_repository()


def get_evaluation_repo() -> EvaluationRepository:
    return Repositories.get_evaluation_repository()