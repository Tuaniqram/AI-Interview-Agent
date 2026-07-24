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


class SessionNotFoundException(AppException):
    def __init__(self, detail: str = "Session not found"):
        super().__init__(detail=detail, status_code=404)


class LLMServiceError(AppException):
    def __init__(self, detail: str = "LLM service error"):
        super().__init__(detail=detail, status_code=502)


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
