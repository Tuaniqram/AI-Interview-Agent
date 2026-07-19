# AI Interview Agent - Development Rules

## Overview

This document establishes the development rules for the AI Interview Agent project. These rules ensure consistency, quality, and maintainability across the codebase.

## For Future Cline Sessions

When working on this project, follow these rules to ensure code quality and consistency:

1. Always read `docs/` before making changes
2. Never hardcode prompts in Python files
3. Maintain the 4-layer architecture (API/Service/Agent/DB)
4. Use type hints everywhere
5. Log all operations
6. Handle errors gracefully
7. Write tests for new features
8. Update documentation when code changes
9. Use Pydantic models for all input/output
10. Don't break backward compatibility

## Before Starting Development

### 1. Read Current Implementation

**Read Order**:
1. `docs/architecture.md` - Understand system architecture
2. `docs/api-design.md` - Know what endpoints exist
3. `docs/database-schema.md` - Know database structure
4. `docs/prompt-engineering.md` - Know prompt strategy
5. `docs/llm-workflow.md` - Know LLM integration patterns
6. `docs/coding-standards.md` - Know code conventions
7. `docs/error-handling.md` - Know error patterns
8. **Current code** - Read actual implementation
9. **Related prompts** - Read if modifying prompts

### 2. Check .clinerules

Always check `.clinerules` in the root directory for project-specific rules.

```bash
# Check .clinerules
cat .clinerules
```

## Coding Rules

### Never Hardcode Prompts

**❌ BAD**:
```python
# app/api/interview.py
evaluation_prompt = f"""
You are an technical interviewer...
AI is Evaluating...
"""
response = llm.invoke(evaluation_prompt)
```

**✅ GOOD**:
```python
# prompts/interview/answer_evaluation.md
# loads prompt from file and injects variables
response = await prompt_loader.load("interview/answer_evaluation.md", {
    "question": question,
    "answer": answer
})
```

### Maintain Layer Separation

**❌ BAD** - Business logic in API:
```python
# app/api/interview.py (BAD)
async def submit_answer(data: dict):
    session = supabase.table("sessions").select("*").execute()
    evaluation = llm.invoke(...)
    supabase.table("messages").insert(...).execute()
    # 100+ lines of business logic here
    return result
```

**✅ GOOD** - API calls service:
```python
# app/api/interview.py (GOOD)
async def submit_answer(request: AnswerRequest):
    result = await interview_service.submit回答(**request.dict())
    return result

# app/services/interview_service.py
async def submit_answer(self, data: dict):
    # Business logic here
    session = await self.session_repo.get(...)

# app/repositories/session_repository.py
async def get(self, session_id: str):
    # Database access only
    pass
```

### Use Type Hints

**❌ BAD**:
```python
async def get_next_question(session_id):
    return result
```

**✅ GOOD**:
```python
from typing import Optional
from pydantic import BaseModel

async def get_next_question(
    company_id: int,
    session_id: str
) -> dict:
    """Get next question for interview."""
    pass
```

### Implement Proper Error Handling

**❌ BAD**:
```python
async def evaluate_answer(data):
    try:
        result = await llm.invoke(...)
        await db.save(result)
        return result
    except Exception:
        return {"error": "Unknown error"}
```

**✅ GOOD**:
```python
async def evaluate_answer(self, data: dict):
    try:
        # Validate
        validated_data = EvaluationRequest(**data)
        
        # Try multiple approaches
        try:
            result = await self._evaluate_with_json(validated_data)
        except LLMServiceError:
            logger.warning("JSON failed, falling back")
            result = await self._evaluate_with_template(validated_data)
        
        # Log success
        logger.info("Evaluation completed")
        return result
        
    except ValidationError as e:
        logger.error("Invalid input")
        raise HTTPException(status_code=422, detail=str(e))
        
    except Exception as e:
        logger.error("Unexpected error", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")
```

### Add Logging

**❌ BAD**:
```python
result = await llm.invoke(prompt)
return result
```

**✅ GOOD**:
```python
import logging
logger = logging.getLogger(__name__)

logger.info("LLM invocation started", extra={
    "prompt_length": len(prompt),
    "session_id": session_id
})

try:
    result = await llm.invoke(prompt)
    logger.info("LLM invocation succeeded", extra={
        "duration_ms": elapsed,
        "tokens": response.usage.total_tokens
    })
    return result
except Exception as e:
    logger.error("LLM invocation failed", extra={
        "error": str(e),
        "session_id": session_id
    }, exc_info=True)
    raise
```

### Use Pydantic Models

**❌ BAD**:
```python
# Don't use dict[str, Any]
async def process(data):
    name = data.get("name")
    age = data.get("age")
    email = data.get("email")
```

**✅ GOOD**:
```python
from pydantic import BaseModel, Field

class UserData(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    age: int = Field(..., ge=0, le=120)
    email: str = Field(..., pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

class UserProcessor:
    async def process(self, data: UserData):
        name = data.name
        age = data.age
        email = data.email
```

### Implement Circuit Breaker for External Services

```python
from circuitbreaker import circuit

@circuit(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=LLMServiceError
)
async def call_llm(self, prompt: str):
    """Call LLM with circuit breaker."""
    return await self.client.invoke(prompt)
```

## File and Directory Rules

### File Naming

- **Python files**: `lowercase_with_underscores.py` (e.g., `interview_service.py`)
- **Configuration files**: `config.py` or `_config.py`
- **Prompt files**: `lowercase_with_underscores.md` in `prompts/` directory
- **Documentation files**: `lowercase_with_underscores.md` in `docs/` directory
- **Test files**: `test_*.py` or `*_test.py` in `tests/` directory

### Directory Structure

```
projectiqram/AI/AI-Interview-Agent/
├── app/
│   ├── api/                    # FastAPI routes only
│   ├── services/               # Business logic
│   ├── agents/                 # AI reasoning (LangGraph)
│   ├── repositories/           # Database access
│   ├── models/                 # Pydantic models
│   ├── config/                 # Configuration
│   ├── graph/                  # LangGraph workflow
│   └── exceptions.py           # Custom exceptions
├── docs/                       # Documentation
├── prompts/                    # LLM prompts
├── tests/                      # Test files
├── scripts/                    # Utility scripts
├── requirements.txt            # Dependencies
├── .clinerules                 # Project-specific rules
└── README.md                   # Project overview
```

### Import Rules

**Order**:
1. Standard library (`import os`, `import logging`)
2. Third-party (`from fastapi import ...`, `from pydantic import ...`)
3. Project imports (`from app.services import ...`)

**Pattern**:
```python
# Standard library
import logging
from typing import Optional, List
import asyncio

# Third-party
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import redis

# Project
from app.config.database import get_supabase
from app.exceptions import SessionNotFoundException
from app.services.interview_service import InterviewService

logger = logging.getLogger(__name__)
```

## Prompt Management Rules

### Prompt File Structure

Every prompt file must follow these sections:

```markdown
# [Prompt Name]

# Purpose
[What this prompt does]

# Inputs
- input1: [description]
- input2: [description]

# Constraints
1. [constraint 1]
2. [constraint 2]

# Instructions
[step-by-step instructions]

# Output Format
[structure and format]

# Example[s]
[examples showing input/output]
```

### Prompt File Naming

```
prompts/
├── system/
│   ├── interviewer_system.md
│   ├── evaluator_system.md
│   └── followup_system.md
├── interview/
│   ├── question_generation.md
│   ├── adaptive_question.md
│   └── interview_flow.md
└── evaluation/
    ├── answer_evaluation.md
    └── scoring_rules.md
```

### Never Hardcode Prompts

Check before committing any code:

```python
# ❌ Search for this pattern
llm.invoke("""
""")
```

If found, extract to prompt file first.

## Testing Rules

### Test Before Committing

```bash
# Run tests
pytest tests/ -v

# Run specific test
pytest tests/services/test_interview_service.py::test_session_creation -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Test Coverage Requirements

- **Core business logic**: 80%+ coverage
- **API endpoints**: 70%+ coverage
- **Database operations**: 90%+ coverage
- **Utility functions**: 70%+ coverage

### Write Unit Tests

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
    assert session.status == "active"
```

### Mock External Services

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_evaluation_with_mock_llm():
    """Test evaluation with mocked LLM."""
    with patch('app.services.llm_manager.LLMManager.invoke') as mock_llm:
        mock_llm.return_value = AsyncMock(
            content='Mocked evaluation response'
        )
        
        result = await service.evaluate_answer(...)
        
        assert result.score > 0
        assert mock_llm.called
```

## Database Rules

### Use Repository Pattern

**❌ BAD**:
```python
# Direct database access in service
async def get_session(id: str):
    response = await supabase.table("sessions").select("*").eq("id", id).execute()
    return response.data[0]
```

**✅ GOOD**:
```python
# Repositories handle DB access
# app/repositories/session_repository.py
class SessionRepository:
    async def get(self, session_id: str) -> dict:
        response = await self.db.table("interview_sessions").select("*").eq("id", session_id).execute()
        if not response.data:
            raise RecordNotFoundException("interview_sessions", "id", session_id)
        return response.data[0]
```

### Use Transactions for Multiple Operations

```python
async def complete_evaluation(self, session_id: str, data: dict):
    """Complete all database operations in one transaction."""
    async with self.db.transaction():
        # Insert message
        messages = await self.db.table("interview_messages").insert(data).execute()
        
        # Insert evaluation
        await self.db.table("interview_evaluations").insert({
            "session_id": session_id,
            "message_id": messages.data[0]["id"],
            **data
        }).execute()
        
        # Update session
        await self.db.table("interview_sessions").update({
            "current_phase": next_phase,
            "current_question_number": new_number
        }).eq("id", session_id).execute()
```

### Never Assume Data Exists

```python
# ❌ BAD
data = supabase.table("sessions").select("*").execute()

# ✅ GOOD
response = await self.db.table("sessions").select("*").eq("id", session_id).execute()
if not response.data:
    raise RecordNotFoundException("session", "id", session_id)
data = response.data[0]
```

## Performance Rules

### Use Caching

```python
from functools import lru_cache

class OptimizationService:
    @lru_cache(maxsize=100)
    async def get_question_template(self, difficulty: int) -> str:
        """Cached question template loading."""
        return await prompt_loader.load(f"prompts/interview/adaptive_question.md", {
            "difficulty": difficulty
        })
```

### Avoid N+1 Queries

**❌ BAD**:
```python
async def get_all_sessions_with_messages():
    sessions = await supabase.table("sessions").select("*").execute()
    
    for session in sessions.data:
        # N+1 query problem
        messages = await supabase.table("messages").select("*").eq("session_id", session.id).execute()
        session["messages"] = messages.data
    
    return sessions.data
```

**✅ GOOD**:
```python
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

### Implement Rate Limiting

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/companies/{company_id}/interview/session")
@limiter.limit("1/minute")  # Limit to 1 request per minute
async def create_session(request: Request, company_id: int):
    pass
```

### Optimize LLM Calls

```python
async def evaluate_answer(self, data: dict):
    """Optimize by caching and validation."""
    # Check cache first
    cache_key = hashlib.md5(f"{data['question']}:{data['answer']}".encode()).hexdigest()
    cached = await llm_cache.get(cache_key)
    if cached:
        return cached
    
    # Validate input
    validated = EvaluationRequest(**data)
    
    # Call LLM with retry
    try:
        result = await self.llm_manager.invoke_with_retry(validated.prompt)
        
        # Cache result
        await llm_cache.set(cache_key, result)
        
        return result
    except LLMServiceError as e:
        # Graceful degradation
        return await self.fallback_evaluation(validated)
```

## Documentation Rules

### Update docs when changing code

**Rule**: Every significant code change requires documentation updates.

**When to update**:
- Adding new endpoints → `docs/api-design.md`
- Adding new tables → `docs/database-schema.md`
- Changing LLM prompts → `docs/prompt-engineering.md`
- Refactoring architecture → `docs/architecture.md`
- Adding utility functions → Update inline docstrings

### Document all public APIs

```python
async def evaluate_answer(
    self,
    job_role: str,
    question: str,
    candidate_answer: str
) -> dict:
    """
    Evaluate candidate answer.
    
    This is a public API method.
    
    Args:
        job_role (str): Target job role
        question (str): Question asked
        candidate_answer (str): Candidate's full answer
        
    Returns:
        dict: Evaluation result with score, strengths, etc.
    
    Raises:
        HTTPException (422): If validation fails
        LLMServiceError: If LLM is unavailable
    
    Example:
        >>> result = await service.evaluate_answer(
        ...     job_role="Software Engineer",
        ...     question="Design a system...",
        ...     candidate_answer="I would use...",
        ... )
        >>> print(result["score"])
        7.5
    """
    pass
```

## Git Workflow Rules

### Commit Messages

**Use conventional commits**:

```bash
feat: add evaluation endpoint
fix: correct difficulty calculation
docs: update API design doc
refactor: extract prompts to external files
test: add unit tests for session creation
chore: update dependencies
```

### Pull Request Process

1. **Feature branch** from `main`
2. **Make changes** following all coding rules
3. **Write tests** for new functionality
4. **Update docs** if needed
5. **Run tests**
6. **Create PR** with description
7. **Address feedback** from code review
8. **Merge** after approval

### Don't Commit Secrets

**Never commit**:
- API keys
- Database credentials
- Environment files
- Sensitive tokens

```bash
# Check if secrets are in git
git diff
git log --all --full-history --source --pretty=format:"%H" -- "**/*.env"
```

## Code Review Checklist

Before asking for a pull request, verify:

**Code Quality**:
- [ ] All files have relevant imports
- [ ] No unused imports
- [ ] Type hints on all parameters and returns
- [ ] Docstrings on public methods
- [ ] No magic numbers (use constants)
- [ ] Consistent naming (snake_case)

**Best Practices**:
- [ ] Proper async/await usage
- [ ] Pydantic validation used
- [ ] Logging added with structured format
- [ ] Error handling implemented
- [ ] No blocking operations in async functions
- [ ] No database operations in API layer

**Testing**:
- [ ] New functionality has tests
- [ ] Existing tests still pass
- [ ] Edge cases covered
- [ ] No breaking changes

**Documentation**:
- [ ] API changes documented
- [ ] Prompt changes documented
- [ ] Database changes documented
- [ ] Code comments where needed

**Security**:
- [ ] No secrets in code
- [ ] Input validation implemented
- [ ] User data sanitized
- [ ] No sensitive data in logs

## Common Anti-Patterns to Avoid

### Anti-Pattern 1: God Object

```python
# ❌ BAD - Does everything
class InterviewManager:
    async def create_session(self, ...): pass
    async def generate_question(self, ...): pass
    async def evaluate_answer(self, ...): pass
    async def save_to_db(self, ...): pass
    async def call_llm(self, ...): pass
    def _helper_function_1(self): pass
    def _helper_function_2(self): pass
    # ... 20+ methods
```

**✅ GOOD** - Separate concerns:

```python
classes -> services, repositories, agents
methods centered around single responsibility
```

### Anti-Pattern 2: Magic Strings

```python
# ❌ BAD
if status == "active":
    ...

# ✅ GOOD
STATUS_ACTIVE = "active"
if status == STATUS_ACTIVE:
    ...
```

### Anti-Pattern 3: Async Without Await

```python
# ❌ BAD
async def process(self):
    result1 = self.llm.invoke(prompt1)  # ❌ Missing await
    result2 = self.db.save(data)         # ❌ Missing await
    return result1 + result2
```

**✅ GOOD**:
```python
# ✅ GOOD
async def process(self):
    result1 = await self.llm.invoke(prompt1)
    result2 = await self.db.save(data)
    return result1 + result2
```

## Continuous Improvement

### Weekly Checklist

- [ ] Review error logs
- [ ] Check for slow operations
- [ ] Verify prompt performance
- [ ] Update dependencies
- [ ] Review code changes
- [ ] Test new features
- [ ] Update documentation

### Monthly Checklist

- [ ] Run full test suite
- [ ] Check code coverage
- [ ] Review performance metrics
- [ ] Audit prompt versions
- [ ] Update dependency versions
- [ ] Review security patches
- [ ] Optimize slow queries

## When in Doubt

**Ask questions**:

1. Read the documentation first
2. Look at similar existing code
3. Check `.clinerules`
4. Ask a teammate
5. Start with a small, testable change

**When not sure about architecture**:

1. Refer to `docs/architecture.md`
2. Check layer separation rules
3. See examples in existing code
4. Validate with team
5. Document your rationale

## Summary

These rules ensure:
- **Consistency**: Code follows same patterns
- **Quality**: Better code through discipline
- **Maintainability**: easier to understand and modify
- **Reliability**: Errors caught early
- **Scalability**: System can grow
- **Security**: Safe handling of data

**Rule #1**: Always document your work.
**Rule #2**: Never hardcode prompts.
**Rule #3**: Test before committing.
**Rule #4**: Use type hints everywhere.
**Rule #5**: Follow the 4-layer architecture.