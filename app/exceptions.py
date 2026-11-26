class AppException(Exception):
    def __init__(self, detail: str = "Application error", status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)


class RecordNotFoundException(AppException):
    def __init__(self, detail: str = "Record not found"):
        super().__init__(detail=detail, status_code=404)


class DatabaseException(AppException):
    def __init__(self, detail: str = "Database error"):
        super().__init__(detail=detail, status_code=500)


class StaleSessionError(Exception):
    """A write was refused: the stored session changed after this copy was read."""

    def __init__(self, session_id: str, version: int):
        super().__init__(f"session {session_id[:12]} changed since version {version} was read")
        self.session_id = session_id
        self.version = version


class SessionNotFoundException(AppException):
    def __init__(self, detail: str = "Session not found"):
        super().__init__(detail=detail, status_code=404)


class LLMServiceError(AppException):
    def __init__(self, detail: str = "LLM service error"):
        super().__init__(detail=detail, status_code=502)


class LLMBudgetExceeded(LLMServiceError):
    """This interview (or its organization today) has used up its LLM calls."""

    def __init__(self, scope: str = "session"):
        super().__init__(detail=f"LLM call budget used up ({scope})")


class LLMTimeoutError(AppException):
    def __init__(self, detail: str = "LLM request timed out"):
        super().__init__(detail=detail, status_code=504)


class LLMRateLimitError(AppException):
    def __init__(self, detail: str = "LLM rate limit exceeded"):
        super().__init__(detail=detail, status_code=429)


class AuthException(AppException):
    def __init__(self, detail: str = "Authentication error"):
        super().__init__(detail=detail, status_code=401)


class OrgException(AppException):
    def __init__(self, detail: str = "Organization error"):
        super().__init__(detail=detail, status_code=400)


class SchedulingException(AppException):
    def __init__(self, detail: str = "Scheduling error"):
        super().__init__(detail=detail, status_code=400)


class PublicInterviewException(AppException):
    def __init__(self, detail: str = "Public interview error"):
        super().__init__(detail=detail, status_code=400)
