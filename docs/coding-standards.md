# AI Interview Agent - Coding Standards

## Overview

This document defines the coding standards and conventions for the AI Interview Agent project. Follow these standards to maintain code quality, consistency, and maintainability.

## Python Version

- **Required**: Python 3.10+
- **Minimum**: Python 3.10

```bash
# Check version
python --version  # Should be 3.10.0 or higher
```

## Dependencies

- Use `requirements.txt` for project dependencies
- Lock versions using `pip freeze > requirements.txt`
- Do not manually edit requirements.txt unless upgrading versions
- Use virtual environments
- Pin dependencies with `==` instead of `>=`

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Import Organization

### Standard Imports
```python
# Standard library
from typing import Optional
import logging
import hashlib

# Third-party
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import asyncio
```

### Project Imports
```python
# Relative imports - use when importing within the same project
from app.config.database import get_supabase
from app.models.llm import llm

# Absolute imports - use when importing from parent or sibling modules
from app.api.interview import router as interview_router
from app.services.interview_service import InterviewService
```

### Import Order
1. Standard library imports (`random`, `datetime`, `json`)
2. Third-party imports (`fastapi`, `pydantic`, `requests`)
3. Project imports (`app.*`)

```python
# ✅ GOOD - Proper import order
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config.database import get_supabase
from app.models.llm import llm
from app.services.interview_service import InterviewService
```

## Type Hints

### Required Type Hints
- All function parameters must have type hints
- All function returns must have type hints
- Complex nested structures should use `TypedDict` or Pydantic models

```python
# ✅ GOOD - Complete type hints
from typing import Optional, List, Tuple
from pydantic import BaseModel

async def get_interview_session(
    company_id: int,
    session_id: str
) -> dict:
    """Get interview session details."""
    
    session = await session_repository.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "id": session.id,
        "company_id": session.company_id,
        "job_role": session.job_role
    }
```

### Types to Use

```python
from typing import (
    Optional,  # For nullable values
    List,      # For ordered lists
    Dict,      # For dictionaries
    Tuple,     # For fixed-size tuples
    Union,     # For union types
    Any,       # For unknown or dynamic types
    Callable,  # For functions
    AsyncFunc  # For async functions (if needed)
)

from pydantic import BaseModel, Field
```

### TypedDict for Complex States
```python
from typing import TypedDict

class InterviewState(TypedDict):
    job_role: str
    company_context: str
    question: str
    candidate_answer: str
    feedback: str
    current_phase: str
```

### Avoid Any When Possible
```python
# ❌ BAD - Too vague
def process_response(response: Any):
    pass

# ✅ GOOD - Specific type or Optional
from pydantic import BaseModel

class EvaluationResult(BaseModel):
    score: float
    feedback: str

def process_response(response: EvaluationResult) -> None:
    pass
```

## Function Design

### Function Naming
- Use `snake_case` for functions and variables
- Use `is_` or `has_` prefix for boolean functions
- Use `to_` or `from_` for conversion functions
- Use `get_`, `set_`, `create_`, `remove_` prefixes for CRUD operations

```python
# ✅ GOOD - Descriptive, snake_case
async def calculate_difficulty_score(
    performance_history: List[float]
) -> tuple[int, int]:
    """Calculate difficulty level based on performance."""
    
    factors = await _calculate_adaptation_factors(...)
    
    difficulty, phase = _determine_next_phase(...)
    
    return difficulty, phase

def is_session_active(session_id: str) -> bool:
    """Check if interview session is active."""
    pass

def to_eval_result(prompt: str) -> EvaluationResult:
    """Convert evaluation prompt to result."""
    pass

async def get_upcoming_question(
    session_id: str
) -> Optional[dict]:
    """Get next question for session."""
    pass
```

### Docstrings
- Always include docstrings for public functions
- Use Google-style or NumPy-style format
- Include parameters, returns, and raises

```python
# ✅ GOOD - Complete docstring
async def evaluate_answer(
    job_role: str,
    question: str,
    candidate_answer: str,
    difficulty_level: int = 1
) -> dict:
    """
    Evaluate a candidate's answer and generate feedback.
    
    Args:
        job_role (str): Target job role for the interview
        question (str): The question that was asked
        candidate_answer (str): The candidate's full response
        difficulty_level (int, optional): Difficulty level (1=easy, 2=medium, 3=hard)
    
    Returns:
        dict: Evaluation result containing score, strengths, weaknesses, and feedback
    
    Raises:
        HTTPException (400): If required parameters are missing
        LLMServiceError: If LLM invocation fails
    
    Note:
        This function calls the LLM asynchronously and may take 3-10 seconds
    """
    pass
```

### Small, Focused Functions
```python
# ❌ BAD - One giant function
async def process_interview_flow(data):
    """
    Process entire interview flow with state management, 
    question generation, answer evaluation, and database updates.
    (100+ lines)
    """

# ✅ GOOD - Broken into smaller functions
async def process_interview_flow(data):
    """Orchestrate the complete interview workflow."""
    session = await self.session_repo.create(data["session_data"])
    question = await self._generate_question(session)
    evaluation = await self._evaluate_answer(question, data["answer"])
    await self.session_repo.update(session.id, evaluation)
    return evaluation

async def _generate_question(self, state: dict) -> str:
    """Generate new interview question based on state."""

async def _evaluate_answer(self, question: str, answer: str) -> Evaluation:
    """Evaluate candidate's answer using LLM."""
```

## Async Programming

### Always Use Async Properly

```python
# ❌ BAD - Blocking synchronous code in async function
async def get_session_data(session_id: str):
    response = supabase.table("sessions").select("*").eq("id", session_id).execute()
    return response.data[0]  # ❌ blocking call

# ✅ GOOD - Or use async properly
async def get_session_data(session_id: str):
    response = await supabase.table("sessions").select("*").eq("id", session_id).execute()
    return response.data[0]
```

### FastAPI Endpoints

```python
from fastapi import FastAPI, Depends

@router.post("/interview/answer")
async def submit_answer(
    data: AnswerRequest,
    # Use deps for authentication
    current_user: User = Depends(get_current_user)
):
    """
    Submit candidate answer.
    
    This endpoint is async because it interacts with LLM and database.
    """
    result = await interview_service.evaluate_answer(**data.dict())
    return result
```

### Non-Blocking Operations

```python
from time import perf_counter

async def fetch_multiple_resources(urls: List[str]) -> List[dict]:
    """
    Fetch multiple resources concurrently.
    
    Using asyncio.gather instead of sequential requests.
    """
    tasks = [fetch_url(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results

async def fetch_url(url: str) -> dict:
    """Fetch a single URL (non-blocking)."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

## Pydantic Models

### Models in Services

```python
# ✅ GOOD - Pydantic models for business logic
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class EvaluationData(BaseModel):
    """Data needed for answer evaluation."""
    
    job_role: str = Field(..., min_length=1, max_length=200)
    question: str = Field(..., min_length=1, max_length=500)
    candidate_answer: str = Field(..., min_length=1, max_length=5000)
    difficulty_level: int = Field(default=1, ge=1, le=3)
    previous_scores: Optional[List[float]] = Field(default_factory=list)
    
    @field_validator("difficulty_level")
    @classmethod
    def validate_difficulty(cls, v):
        if v < 1 or v > 3:
            raise ValueError("Difficulty must be 1, 2, or 3")
        return v
```

### Validation Outside Python

```python
# ❌ BAD - No validation in service
await interview_service.evaluate_answer(
    job_role=data.get("job_role"),  # Can be empty
    question=data.get("question"),  # Can be None
    candidate_answer=data.get("answer")  # Can be huge
)

# ✅ GOOD - Use Pydantic validation
from pydantic import BaseModel, ValidationError

class AnswerRequest(BaseModel):
    job_role: str
    question: str
    candidate_answer: str

try:
    validated_data = AnswerRequest(**data)
    result = await interview_service.evaluate_answer(**validated_data.dict())
except ValidationError as e:
    raise HTTPException(status_code=422, detail=str(e))
```

## Error Handling

### Custom Exceptions
```python
# app/exceptions.py
class InterviewException(Exception):
    """Base class for interview exceptions."""
    pass

class SessionNotFoundException(InterviewException):
    """Raised when session is not found."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session {session_id} not found")

class InvalidStateException(InterviewException):
    """Raised when interview is in unexpected state."""
    pass

class LLMServiceError(InterviewException):
    """Raised when LLM operations fail."""
    pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# ✅ GOOD - Structured logging
async def evaluate_answer(self, data: dict) -> Evaluation:
    """Evaluate candidate answer."""
    
    logger.info(
        "Starting evaluation",
        extra={
            "job_role": data["job_role"],
            "difficulty": data["difficulty_level"],
            "answer_length": len(data["candidate_answer"])
        }
    )
    
    try:
        result = await self._call_llm(data)
        
        logger.info(
            "Evaluation complete",
            extra={
                "score": result.score,
                "duration_ms": result.duration_ms
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Evaluation failed",
            extra={
                "job_role": data["job_role"],
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
        raise
```

## Logging Levels

```python
import logging
from loguru import logger

logger.debug("Debug information for troubleshooting")

logger.info("Important business events (session created, answered, completed)")

logger.warning("Warning events (rate limits, retries, degraded performance)")

logger.error("Errors that don't break execution")

logger.critical("Critical errors that require immediate attention")
```

## Constants

### Define at Module Level

```python
# ✅ GOOD - Module-level constants
INTRO_PHASE_COUNT = 2
EXPERIENCE_PHASE_COUNT = 3
TECHNICAL_PHASE_COUNT = 5
BEHAVIORAL_PHASE_COUNT = 3
CONCLUSION_PHASE_COUNT = 10

TOTAL_QUESTION_BUDGET = (
    INTRO_PHASE_COUNT +
    EXPERIENCE_PHASE_COUNT +
    TECHNICH_PHASE_COUNT +
    BEHAVIORAL_PHASE_COUNT +
    CONCLUSION_PHASE_COUNT
)

PHASE_TEMPLATES = {
    "intro": {
        "count": INTRO_PHASE_COUNT,
        "focus": "Build rapport, understand candidate background",
    },
    "technical": {
        "count": TECHNICAL_PHASE_COUNT,
        "focus": "Evaluate core technical abilities",
    },
    # ... more phases
}
```

### Use Constants, Not Magic Numbers

```python
# ❌ BAD - Magic numbers
if score > 7.0:
    next_difficulty = 3

if response[3] == "200":
    return True

# ✅ GOOD - Use named constants
if score > SCORES_BETWEEN_HARD_OR_MEDIUM:
    next_difficulty = DIFFICULTY_HARD

if response.status_code == HTTPStatus.OK:
    return True
```

## Database Operations

### Singleton Access

```python
# ✅ GOOD - Singleton from config
from app.config.database import get_supabase

supabase = get_supabase()  # Global singleton

# Use async methods
async def get_session(session_id: str):
    response = await supabase.table("sessions").select("*").eq("id", session_id).execute()
```

### No N+1 Queries

```python
# ❌ BAD - N+1 problem
async def get_all_sessions():
    sessions = await supabase.table("sessions").select("*").execute()
    
    for session in sessions.data:
        # N+1 query problem
        messages = await supabase.table("messages").select("*").eq("session_id", session.id).execute()
        session["messages"] = messages.data
    
    return sessions.data
```

### Use Batch Operations

```python
# ✅ GOOD - Single query with joins
async def get_session_with_messages(session_id: str):
    response = await supabase.table("sessions").select(`
        *,
        messages (
            id,
            content,
            created_at
        )
    `).eq("id", session_id).execute()
    
    return response.data[0]
```

## Code Organization

### File Structure

```
app/
├── api/              # FastAPI routes only
│   ├── __init__.py
│   ├── company.py
│   ├── interview.py
│   └── general.py
├── services/         # Business logic only
│   ├── __init__.py
│   ├── llm_service.py
│   ├── interview_service.py
│   └── database_service.py
├── agents/           # AI reasoning only
│   ├── __init__.py
│   ├── interviewer.py
│   ├── evaluator.py
│   └── retrieval.py
├── repositories/     # Database access
│   ├── __init__.py
│   ├── session_repository.py
│   └── message_repository.py
├── models/           # Pydantic models
│   ├── __init__.py
│   └── llm.py
├── config/           # Configuration
│   ├── __init__.py
│   ├── database.py
│   └── pinecone.py
├── graph/            # LangGraph workflows
│   ├── __init__.py
│   ├── workflow.py
│   └── company_workflow.py
└── exceptions.py     # Custom exceptions
```

### Module Initialization

```python
# ✅ GOOD - Clear module structure
import logging
from app.config import config

logger = logging.getLogger(__name__)
config.logger = logger

# Execute single main function
logger.info("Initializing module...")
```

## Testing

### Import Testing Utilities

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

### Test Structure

```python
# tests/services/test_interview_service.py
import pytest
from app.services.interview_service import InterviewService

@pytest.mark.asyncio
@pytest.mark.integration
async def test_session_creation():
    """Test that session is created correctly."""
    service = InterviewService(supabase)
    
    session = await service.create_session(
        company_id=1,
        job_role="Software Engineer"
    )
    
    assert session is not None
    assert session.job_role == "Software Engineer"
```

## Code Review Checklist

Before submitting code, verify:

### Code Quality
- [ ] All files have relevant imports
- [ ] No unused imports
- [ ] Type hints on all parameters and returns
- [ ] Docstrings on public functions (Google-style)
- [ ] No magic numbers (use constants)
- [ ] Consistent naming (snake_case)

### Best Practices
- [ ] Proper async/await usage
- [ ] Pydantic validation used
- [ ] Logging added for critical operations
- [ ] Error handling implemented
- [ ] No blocking operations in async functions
- [ ] No database operations in API layer

### Testing
- [ ] Unit tests for business logic
- [ ] Integration tests for API endpoints
- [ ] Edge cases covered
- [ ] No test dependencies

### Documentation
- [ ] Updated architecture documentation
- [ ] New prompts added to prompts/ directory
- [ ] API endpoints documented
- [ ] Database schema documented

## Performance Best Practices

### Caching

```python
from functools import lru_cache

class OptimizationService:
    """Service with caching for expensive operations."""
    
    @lru_cache(maxsize=100)
    def get_question(self, job_role: str, phase: str) -> str:
        """Cached question generation."""
        pass
    
    @lru_cache(maxsize=50)
    def get_evaluation_template(self, difficulty: int) -> str:
        """Cached evaluation prompt template."""
        pass
```

### Avoid Unnecessary Computations

```python
# ❌ BAD - Recomputes every time
async def process_data(data: dict):
    if data.get("fresh"):
        await refresh_all_cache()
    # ... rest of logic

# ✅ GOOD - Check carefully before expensive ops
async def process_data(data: dict):
    if data.get("fresh"):
        await refresh_all_cache()
        data["fresh"] = False
    
    # ... rest of logic
```

## Security Best Practices

### Validate All Inputs

```python
from pydantic import BaseModel, Field, field_validator

class AnswerRequest(BaseModel):
    """Request with input validation."""
    
    candidate_answer: str = Field(
        ...,
        min_length=1,
        max_length=5000
    )
    
    @field_validator("candidate_answer")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """Sanitize user input."""
        # Remove potential SQL injection patterns
        v = v.replace("'", "")
        return v
```

### Never Log Sensitive Data

```python
# ❌ BAD - Logging sensitive data
logger.info(f"User provided answer: {user_answer}")

# ✅ GOOD - Only log what's needed
logger.info(
    "User answered question",
    extra={
        "question_id": question_id,
        "timestamp": datetime.now().isoformat()
    }
)
```

## Code Style

### PEP 8 Compliant

- Use `4 spaces` for indentation
- Black formatter recommended
- Flake8 for linting
- isort for import sorting

```bash
# Formatters
black app/services/ interview.py
isort -rc app/services/ interview.py
flake8 app/services/
```

### Line Length

- Maximum line length: **100 characters** (with some exceptions for clarity)
- Break long lines at logical points

```python
# ✅ GOOD - Properly broken lines
result = await llm_manager.invoke(
    prompt=evaluation_prompt,
    system_prompt=interviewer_system_prompt,
    temperature=0.7,
    max_retries=3
)

# Or use parentheses if readability is maintained
eval_response = await self._call_llm(
    question_data, candidate_answer, 
    job_role, difficulty_level, conversation_history
)
```

## Common Patterns

### Repository Pattern

```python
# repositories/base_repository.py
class BaseRepository:
    def __init__(self, db):
        self.db = db or get_supabase()

    async def create(self, data: dict) -> dict:
        response = await self.db.table(self._table_name).insert(data).execute()
        return response.data[0]

# repositories/session_repository.py
class SessionRepository(BaseRepository):
    _table_name = "interview_sessions"
```

### Service Layer

```python
# services/interview_service.py
class InterviewService:
    def __init__(self, session_repo, question_service, evaluation_service):
        self.session_repo = session_repo
        self.question_service = question_service
        self.evaluation_service = evaluation_service
```

### Dependency Injection

```python
# Use FastAPI dependencies
@router.post("/interview/session")
async def create_session(
    request: SessionStartRequest,
    interview_service: InterviewService = Depends(get_interview_service)
):
    """Create interview session using injected service."""
    return await interview_service.create_session(
        company_id=request.company_id,
        job_role=request.job_role
    )
```

## Performance Metrics

Track these metrics to monitor code performance:

```python
from time import perf_counter

class PerformanceTracker:
    def __init__(self):
        self.metrics = {}
    
    async def track(self, func_name: str):
        """Track execution time of async function."""
        start = perf_counter()
        
        yield
        
        duration = perf_counter() - start
        
        metrics = self.metrics.get(func_name, [])
        metrics.append(duration)
        self.metrics[func_name] = metrics
```

## Conclusion

Following these coding standards ensures:
1. **Consistency**: Code follows the same patterns throughout
2. **Maintainability**: Easy to understand and modify
3. **Reliability**: Type safety and validation catch errors early
4. **Performance**: Async operations and caching used appropriately
5. **Security**: Input validation and sensitive data protection

Code should be:
- **Clean**: Easy to read with good naming
- **Small**: Functions do one thing well
- **Testable**: Clear interfaces and dependencies
- **Documented**: Well-commented and self-explanatory
- **Secure**: All inputs validated, sensitive data protected