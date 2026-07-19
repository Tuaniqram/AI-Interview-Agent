"""
Custom exceptions for interview agent system.
"""
from typing import Optional


class InterviewException(Exception):
    """
    Base exception for interview-related errors.
    All custom exceptions should inherit from this.
    """
    
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "INTERVIEW_ERROR"
        super().__init__(self.message)


class SessionException(InterviewException):
    """Base exception for session-related errors."""
    pass


class SessionNotFoundException(SessionException):
    """Raised when session is not found."""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session {session_id} not found",
            code="SESSION_NOT_FOUND"
        )
        self.session_id = session_id


class SessionStateException(SessionException):
    """Raised when session is in invalid state."""
    
    def __init__(self, session_id: str, invalid_state: str):
        super().__init__(
            message=f"Session {session_id} is in invalid state: {invalid_state}",
            code="INVALID_SESSION_STATE"
        )
        self.session_id = session_id
        self.invalid_state = invalid_state


class RecordNotFoundException(InterviewException):
    """Raised when database record is not found."""
    
    def __init__(self, table: str, identifier: str, value: str):
        super().__init__(
            message=f"Record not found in {table} with {identifier}: {value}",
            code=f"{table.upper()}_NOT_FOUND"
        )
        self.table = table
        self.identifier = identifier
        self.value = value


class LLMServiceError(InterviewException):
    """Raised when LLM operations fail."""
    
    def __init__(self, message: str, code: str = "LLM_SERVICE_ERROR"):
        super().__init__(message, code)
        self.code = code


class LLMTimeoutError(LLMServiceError):
    """Raised when LLM times out."""
    
    def __init__(self, timeout: int):
        super().__init__(
            message=f"LLM service timed out after {timeout} seconds",
            code="LLM_TIMEOUT"
        )
        self.timeout = timeout


class LLMRateLimitError(LLMServiceError):
    """Raised when LLM API rate limit is exceeded."""
    
    def __init__(self, retry_after: int, limit: int):
        super().__init__(
            message=f"LLM API rate limit exceeded. Limit: {limit} requests/min. Retry after {retry_after} seconds.",
            code="LLM_RATE_LIMIT"
        )
        self.retry_after = retry_after
        self.limit = limit


class DatabaseException(InterviewException):
    """Raised when database operations fail."""
    pass