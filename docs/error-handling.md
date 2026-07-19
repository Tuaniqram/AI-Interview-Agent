# AI Interview Agent - Error Handling

## Overview

This document describes the error handling strategy for the AI Interview Agent. It covers exception types, error handling patterns, logging, and user-facing error messaging.

## Error Handling Philosophy

### Goals

1. **Graceful Failure**: System should fail without breaking
2. **Meaningful Errors**: Users and developers understand what failed
3. **Security**: Never expose sensitive errors to users
4. **Debugability**: Logs contain enough context for troubleshooting
5. **Consistency**: Error responses follow standard format

### Core Principles

- Never crash the entire server from user input errors
- Always log errors before raising exceptions
- Use appropriate HTTP status codes
- Provide clear, actionable error messages
- Handle framework errors separately from business errors

## Exception Hierarchy

### Custom Exceptions

Create exceptions in `app/exceptions.py`:

```python
# app/exceptions.py
from typing import Optional
from fastapi import HTTPException

class InterviewException(Exception):
    """
    Base exception for interview-related errors.
    All custom errors should inherit from this.
    """
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
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

class RecordNotFoundException(DatabaseException):
    """Raised when a database record is not found."""
    def __init__(self, table: str, identifier: str, value: str):
        super().__init__(
            message=f"Record not found in {table} with {identifier}: {value}",
            code=f"{table.upper()}_NOT_FOUND"
        )
        self.table = table
        self.identifier = identifier
        self.value = value

# And so on for other exception types...
```

### HTTPException Mapping

```python
# app/api/interview.py
from fastapi import HTTPException, status
from app.exceptions import SessionNotFoundException

@router.post("/companies/{company_id}/interview/session")
async def start_interview_session(
    request: SessionStartRequest,
    company_id: int
):
    """Create interview session."""
    try:
        session = await interview_service.create_session(
            company_id=company_id,
            job_role=request.job_role
        )
        return session
        
    except SessionNotFoundException as e:
        # Note: SessionNotFoundException shouldn't happen here,
        # but if it does, map to 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
        
    except Exception as e:
        logger.error("Session creation failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create interview session due to an internal error"
        )
```

## Error Response Format

### Standard Error Response

```json
{
  "detail": {
    "message": "User-readable error message",
    "code": "ERROR_CODE",
    "timestamp": "2026-07-18T15:30:00Z",
    "request_id": "req_abc123"
  },
  "path": "/api/v1/interview/session"
}
```

### Validation Error Response

```json
{
  "detail": [
    {
      "loc": ["body", "session_id"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    {
      "loc": ["body", "job_role"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.min_length",
      "input": "",
      "ctx": {
        "min_length": 1
      }
    }
  ]
}
```

## Error Logging Strategy

### Criticality Levels

```python
import logging

logger = logging.getLogger(__name__)

# Critical: System-wide failures (all services down, security breaches)
logger.critical("Database connection lost, all queries failing")

# Error: Individual failures that don't crash system
logger.error("Failed to evaluate answer", extra={
    "session_id": session_id,
    "user_message": "Evaluation temporarily unavailable"
})

# Warning: Recoverable issues (rate limits, retries)
logger.warning("LLM API rate limit exceeded, retrying after delay")

# Info: Normal business operations (good events)
logger.info("Session created successfully")

# Debug: Detailed troubleshooting information
logger.debug("Entered _evaluate_answer function with data")
```

### Structured Logging

```python
async def submit_answer(
    self,
    company_id: int,
    session_id: str,
    answer: str
):
    """Submit candidate answer with detailed error logging."""
    
    try:
        # Validate session exists
        session = await self.session_repo.get(session_id)
        if not session:
            logger.error(
                "Cannot evaluate answer: session not found",
                extra={
                    "company_id": company_id,
                    "session_id": session_id,
                    "action": "submit_answer"
                }
            )
            raise SessionNotFoundException(session_id)
        
        # Validate session state
        if session.status != "active":
            logger.error(
                "Cannot evaluate answer: session not active",
                extra={
                    "company_id": company_id,
                    "session_id": session_id,
                    "current_status": session.status,
                    "action": "submit_answer"
                }
            )
            raise SessionStateException(session_id, session.status)
        
        # Proceed with evaluation
        logger.info(
            "Starting answer evaluation",
            extra={
                "company_id": company_id,
                "session_id": session_id,
                "answer_length": len(answer),
                "action": "submit_answer"
            }
        )
        
        result = await self._evaluate_answer(answer)
        await self.session_repo.log_answer(session_id, answer)
        
        logger.info(
            "Answer evaluation completed successfully",
            extra={
                "company_id": company_id,
                "session_id": session_id,
                "score": result.score,
                "feedback_length": len(result.feedback),
                "action": "submit_answer"
            }
        )
        
        return result
        
    except SessionNotFoundException as e:
        # Don't log at ERROR level, this is a user error
        logger.debug(
            "Session not found during evaluation",
            extra={"session_id": session_id}
        )
        raise
        
    except Exception as e:
        logger.error(
            "Answer evaluation unexpectedly failed",
            extra={
                "company_id": company_id,
                "session_id": session_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            },
            exc_info=True  # Includes full traceback
        )
        raise
```

## LLM Error Handling

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import time

class LLMManager:
    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=(
            retry.if_exception_type(ConnectionError) |
            retry.if_exception_type(ConnectionTimeout)
        )
    )
    async def invoke_with_retry(self, prompt: str):
        """Invoke LLM with automatic retries for transient errors."""
        
        attempts = 0
        last_exception = None
        
        while attempts < self.max_retries:
            attempts += 1
            
            try:
                start_time = time.time()
                response = await self.client.invoke(prompt)
                duration = time.time() - start_time
                
                logger.info(
                    "LLM invocation succeeded",
                    extra={
                        "attempts": attempts,
                        "duration_ms": round(duration * 1000, 2)
                    }
                )
                
                return response
                
            except RateLimitError as e:
                last_exception = e
                logger.warning(
                    "LLM rate limit hit, retrying",
                    extra={
                        "attempts": attempts,
                        "retry_after": e.retry_after,
                        "limit": e.limit
                    }
                )
                
            except ConnectionError as e:
                last_exception = e
                logger.warning(
                    "LLM connection error, retrying",
                    extra={
                        "attempts": attempts,
                        "error": str(e)
                    }
                )
                
            except Exception as e:
                logger.error(
                    "LLM error during invocation",
                    extra={
                        "attempts": attempts,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise LLMServiceError(f"LLM invocation failed after {attempts} retries: {str(e)}")
        
        # All retries failed
        raise last_exception or LLMServiceError(f"LLM invocation failed after {attempts} retries")
```

### Graceful Fallbacks

```python
async def evaluate_answer(
    self,
    question: str,
    answer: str,
    job_role: str
):
    """Evaluate answer with graceful fallback on LLM failure."""
    
    try:
        # Try structured JSON response
        return await self._evaluate_with_json(question, answer, job_role)
        
    except JSONDecodeError as e:
        logger.warning("JSON parsing failed, falling back to text extraction", exc_info=True)
        # Fallback to text-based evaluation
        return await self._evaluate_with_text(question, answer, job_role)
        
    except LLMServiceError as e:
        logger.error("LLM evaluation failed, using default", exc_info=True)
        # Fallback to template-based evaluation
        return await self._evaluate_with_template(question, job_role)
        
    except Exception as e:
        logger.critical("All evaluation approaches failed", exc_info=True)
        # Last resort: return minimal error response
        return {
            "score": 5.0,
            "feedback": "Evaluation temporarily unavailable. Please try again later.",
            "strengths": "N/A",
            "weaknesses": "N/A",
            "error": True
        }
```

## Database Error Handling

### Transaction Management

```python
async def complete_evaluation_with_transaction(
    self,
    session_id: str,
    evaluation_data: dict,
    question_data: dict
):
    """Complete evaluation with database transaction."""
    
    # Use context manager for transaction
    try:
        async with self.db.transaction():
            # Insert message
            message = await self.db.table("interview_messages").insert({
                **question_data,
                **evaluation_data,
                **data
            }).execute()
            
            # Insert evaluation
            await self.db.table("interview_evaluations").insert({
                "session_id": session_id,
                "message_id": message.data[0]["id"],
                **evaluation_data
            }).execute()
            
            # Update session
            await self.db.table("interview_sessions").update({
                "current_phase": next_phase,
                "current_question_number": new_number,
                "final_score": final_score,
                "status": "completed",
                "final_feedback": evaluation_detail
            }).eq("id", session_id).execute()
            
        return {"success": True}
        
    except DatabaseException as e:
        # Database errors are rolls back automatically
        logger.error("Database transaction failed", extra={
            "session_id": session_id,
            "error_type": type(e).__name__,
            "error": str(e)
        })
        
        # Return optimistic response to user, but mark as error in system
        return {
            "success": False,
            "message": "Transaction processing issue. Please try again.",
            "error_code": "DB_TRANSACTION_FAILED"
        }
```

## Rate Limiting and Throttling

### API Rate Limiting

```python
from fastapi import FastAPI, Request, HTTPException, status
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/companies/{company_id}/interview/session")
@limiter.limit("1/minute")  # Limit to 1 request per minute
async def start_interview_session(
    request: Request,
    company_id: int
):
    """Create interview session with rate limiting."""
    pass

@router.post("/companies/{company_id}/interview/answer")
@limiter.limit("10/minute")  # 10 answers per minute per company
async def submit_answer(
    request: Request,
    company_id: int
):
    """Submit answer with rate limiting."""
    pass
```

### Error Response for Rate Limit

```python
class RateLimitExceededError(HTTPException):
    """Custom exception for rate limiting."""
    def __init__(self, limit: int, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {limit} requests per minute. Retry after {retry_after} seconds."
        )
        self.retry_after = retry_after
```

## Validation Error Handling

### Pydantic Validation

```python
from fastapi import HTTPException
from pydantic import ValidationError

class AnswerRequest(BaseModel):
    job_role: str = Field(..., min_length=1, max_length=200)
    session_id: str = Field(..., pattern="^[0-9a-f-]{36}$")
    question: str = Field(..., min_length=1, max_length=2000)
    candidate_answer: str = Field(..., min_length=1, max_length=10000)
    difficulty_level: int = Field(default=1, ge=1, le=3)

@router.post("/answer")
async def submit_answer(
    request: AnswerRequest
):
    """Submit candidate answer with validation."""
    
    try:
        validated_data = AnswerRequest(**request.data)
    except ValidationError as e:
        # Convert Pydantic errors to HTTP response
        errors = [
            {
                "field": loc[-1],
                "message": msg,
                "type": error_type
            }
            for error in e.errors()
            for loc, msg, error_type in [(error["loc"], error["msg"], error["type"])]
        ]
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "errors": errors,
                "type": "validation_error",
                "code": "VALIDATION_ERROR"
            }
        )
```

## Security Error Handling

### Never Expose Sensitive Information

```python
# ❌ BAD - Exposes internal details
@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    try:
        session = await session_repo.get(session_id)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}\nTable: interview_sessions\nTraceback: {traceback.format_exc()}"
        )

# ✅ GOOD - Generic error for users
@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    try:
        session = await session_repo.get(session_id)
        return session
    except Exception as e:
        logger.error(
            "Failed to retrieve session",
            extra={
                "session_id": session_id,
                "error": str(e),
                "type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve session. Please try again later."
        )
```

### Secrets Protection

```python
# ❌ BAD - Logs secrets
logger.info(f"Processing payment with card: {credit_card_number}")

# ✅ GOOD - Don't log secrets
logger.info("Processing payment", extra={
    "card_last4": credit_card_number[-4:],
    "amount": amount,
    "status": "success"
})

# ❌ BAD - Expose sensitive errors
raise HTTPException(
    status_code=400,
    detail=f"Invalid API key: {api_key}"
)

# ✅ GOOD - Generic error
logger.warning(
    "Invalid API key provided",
    extra={
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }
)
raise HTTPException(
    status_code=401,
    detail="Invalid API key"
)
```

## Circuit Breaker Pattern

```python
from circuitbreaker import circuit

@circuit(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=LLMServiceError
)
async def call_llm_service(self, prompt: str):
    """Call LLM service with circuit breaker."""
    return await self.client.invoke(prompt)
```

When the LLM service fails 5 times in a row:
1. Circuit opens (prevents further failures)
2. Returns predefined fallback
3. Waits for 60 seconds (recovery window)
4. Tests service health
5. Closes circuit if healthy

## Error Response Templates

### HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Dependency unavailable

### User-Facing Error Messages

```python
# Generic error messages (don't leak system details)
USER_MESSAGES = {
    "SESSION_NOT_FOUND": "Interview session not found. Please restart the interview.",
    "SESSION_COMPLETED": "Interview has already been completed.",
    "LLM_SERVICE_ERROR": "Interview evaluation is temporarily unavailable. Please try again later.",
    "LLM_TIMEOUT": "Service is busy. Please wait a moment and try again.",
    "RATE_LIMIT_ERROR": "Too many requests. Please slow down.",
    "DATABASE_ERROR": "Service temporarily unavailable. Please try again.",
    "VALIDATION_ERROR": "Invalid input. Please check your request and try again.",
}

# Developer error messages (include context)
dev_error_message = f"{USER_MESSAGES.get(code, 'An unexpected error occurred')}. [Error: {code}]"
```

## Monitoring and Alerting

### Error Tracking

```python
# app/monitoring.py
class ErrorTracker:
    def __init__(self):
        self.error_counts = {}
        self.cumulative_errors = 0
    
    def record_error(
        self,
        error_type: str,
        error_code: str,
        user_context: Optional[dict] = None
    ):
        """Record error for monitoring and alerting."""
        
        key = f"{error_type}:{error_code}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        self.cumulative_errors += 1
        
        # Log with context
        logger.error(
            "Error occurred",
            extra={
                "error_type": error_type,
                "code": error_code,
                "count": self.error_counts[key],
                "total_errors": self.cumulative_errors,
                "user_context": user_context
            }
        )
        
        # Send to monitoring service (Sentry, Datadog, etc.)
        # alert_factory.create_alert(...)
    
    def get_error_rate(self, window_seconds: int = 60) -> float:
        """Get error rate over time window."""
        # Calculate rate based on logs in time window
        pass

error_tracker = ErrorTracker()
```

### Alert Thresholds

```python
# app/alerts.py
class ErrorAlerts:
    def __init__(self):
        self.thresholds = {
            "LLM_TIMEOUT": 10,  # Alert on 10 timeouts in a minute
            "LLM_RATE_LIMIT": 20,
            "DATABASE_ERROR": 5,
        }
    
    def check(self, error_type: str, count: int):
        """Check if error should trigger alert."""
        threshold = self.thresholds.get(error_type, 5)
        
        if count >= threshold:
            # Send alert
            alert_service.send_alert(
                level="ERROR",
                message=f"High error rate for {error_type}: {count} occurrences",
                threshold=threshold
            )
```

## Testing Error Cases

### Unit Testing Error Handling

```python
# tests/services/test_interview_service.py
import pytest
from app.exceptions import SessionNotFoundException
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_empty_answer_validation():
    """Test that empty answer is rejected."""
    service = InterviewService(supabase)
    
    with pytest.raises(HTTPException) as exc_info:
        await service.evaluate_answer(
            question="Test question",
            answer="",  # Empty
            job_role="Software Engineer"
        )
    
    assert exc_info.value.status_code == 422
    assert "must have at least 1 characters" in exc_info.value.detail

@pytest.mark.asyncio
async def test_invalid_phase_transition():
    """Test that invalid phase transition throws error."""
    service = InterviewService(supabase)
    
    session = await service.create_session(
        company_id=1,
        job_role="Software Engineer"
    )
    session["current_phase"] = "conclusion"  # Already completed
    
    with pytest.raises(SessionStateException) as exc_info:
        await service.get_next_question(
            company_id=1,
            session_id=session["id"]
        )
    
    assert "invalid state" in exc_info.value.message.lower()

@pytest.mark.asyncio
async def test_llm_timeout_handling():
    """Test graceful handling of LLM timeout."""
    with patch.object(llm_manager, 'invoke', side_effect=LLMTimeoutError(30)):
        result = await service.evaluate_answer_with_fallback(
            question="Test",
            answer="Test answer"  
        )
        
        assert "error" in result
        assert result.get("error") is True
```

## Best Practices Summary

### ✅ DO

1. Catch specific exceptions before generic ones
2. Log all errors before raising
3. Use appropriate HTTP status codes
4. Never expose sensitive details in error messages
5. Provide graceful fallbacks for LLM failures
6. Use transaction management for database writes
7. Implement retry logic for transient errors
8. Use rate limiting for API endpoints
9. Record errors for monitoring and alerting
10. Write tests for error handling paths

### ❌ DON'T

1. Catch generic `Exception` too broadly
2. Log passwords, API keys, or secrets
3. Crash the server from user errors
4. Return internal stack traces to users
5. Assume all errors should stop processing
6. Never use rate limiting
7. Forget to handle database transaction failures
8. Only log errors, never warnings for failures
9. Assume retries always succeed
10. Ignore rate limit errors

## Common Error Patterns

### Pattern 1: LLM Failure in Async Flow

```python
async def process_with_llm_fallback(data):
    try:
        # Primary path - works 95% of the time
        result = await llm_service.invoke(data)
        return result
    except LLMServiceError as e:
        logger.warning("LLM failed, using fallback", exc_info=True)
        # Fallback path - works 5% of the time
        result = await fallback_service(data)
        return result
```

### Pattern 2: Database Transaction Failure

```python
async def critical_update_workflow(session_id: str, updates: dict):
    try:
        async with db.transaction():
            # Multiple dependent updates
            await db.update("table1", updates["updates1"])
            await db.update("table2", updates["updates2"])
            await db.update("table3", updates["updates3"])
        
        logger.info("Transaction completed successfully")
        return {"success": True}
        
    except DatabaseException as e:
        logger.error("Transaction rolled back", exc_info=True)
        # Mark system state as inconsistent
        await db.mark_transaction_failed(session_id)
        
        # Return optimistic response
        return {
            "success": False,
            "message": "Processing issue. Please try again.",
            "state_preserved": True
        }
```

### Pattern 3: Validation Rejection

```python
def validate_and_handle(data: dict):
    # Infer validation first
    try:
        validated = RequestSchema(**data)
    except ValidationError as e:
        # Detailed validation response
        raise HTTPException(
            status_code=422,
            content={
                "detail": e.errors(),
                "error_type": "validation_error",
                "message": "Invalid request data"
            }
        )
    
    # If validation passes, proceed
    try:
        result = business_logic(validated)
        return result
    except ValueError as e:
        # Business logic validation error
        raise HTTPException(
            status_code=400,
            detail={
                "error_type": "business_logic_error",
                "message": str(e)
            }
        )