# AI Interview Agent - Architecture Documentation

## Overview

This document provides a comprehensive overview of the AI Interview Agent architecture after Phase 2 refactoring.

## Architecture Summary

The system follows a clean **5-Layer Architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Frontend)                         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: API Layer (app/api/)                             │
│  - Request Validation                                       │
│  - Response Formatting                                       │
│  - Error Handling                                            │
│  - Delegates to Service Layer                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Service Layer (app/services/)                     │
│  - Business Logic                                            │
│  - State Management                                          │
│  - Flow Orchestration                                        │
│  - Domain Rules                                              │
└────────────────┬────────────────┬───────────────────────────┘
                 ▼                ▼
┌────────────────────────┐  ┌────────────────────────────┐
│  Layer 3: Prompt Layer │  │  Layer 4: Repository Layer │
│  (app/services)        │  │  (app/repositories/)       │
│  - Prompt Loader       │  │  - Database Access         │
│  - LLM Manager         │  │  - Data Abstraction        │
│                        │  │  - Error Handling          │
└────────────────────────┘  └─────────────┬───────────────┘
                                          │
                                          ▼
                              ┌─────────────────────────┐
                              │  Layer 5: Database      │
                              │  (Supabase/PostgreSQL)  │
                              └─────────────────────────┘
```

## New Components (Phase 2)

### 1. Repository Pattern (`app/repositories/`)

**Purpose**: Abstract database operations from business logic

**Files**:
- `base_repository.py` - Base class with CRUD operations
- `session_repository.py` - Session-specific operations
- `message_repository.py` - Message-specific operations
- `repositories.py` - Factory for repository access

**Benefits**:
- ✅ Centralized error handling
- ✅ Consistent database operations
- ✅ Easy database migrations
- ✅ Better testability
- ✅ Clean separation of concerns

**Example Usage**:
```python
# Get session
session = await session_repo.get_session(session_id)

# Create message
await message_repo.create_candidate_answer(
    session_id=session_id,
    role="candidate",
    candidate_answer=answer,
    question_number=idx,
    phase=current_phase,
    score=score
)
```

### 2. Service Layer (`app/services/`)

**Purpose**: Contain all business logic and orchestration

**Files**:
- `interview_service.py` - Main interview workflow logic
- `llm_service.py` - Centralized LLM management with caching
- `prompt_loader.py` - External prompt template loading
- `repositories.py` - Repository factory

**Key Classes**:

#### InterviewService
Main business logic for interview management:

```python
class InterviewService:
    async def start_interview(company_id, job_role) -> dict:
        """Create new interview session"""
    
    async def generate_next_question(...) -> dict:
        """Generate adaptive question based on performance"""
    
    async def evaluate_answer(...) -> dict:
        """Evaluate candidate answer and return feedback"""
    
    async def handle_answer_submit(...) -> dict:
        """Complete flow: evaluate, update state, generate follow-up"""
```

#### LLMService
Centralized LLM management:

```python
class LLMService:
    async def invoke(prompt, temperature, ...) -> str:
        """Invoke LLM with caching and retry logic"""
    
    async def invoke_structured(prompt, pydantic_model) -> Any:
        """Invoke LLM and parse structured output"""
    
    def clear_cache():
        """Clear response cache"""
```

#### PromptLoader
External prompt template management:

```python
def load_prompt(category, filename, **vars) -> str:
    """Load and render prompt template"""
```

### 3. Error Handling (`app/exceptions.py`)

**Custom Exceptions Hierarchy**:

```
InterviewException
├── SessionException
│   ├── SessionNotFoundException
│   └── SessionStateException
├── RecordNotFoundException (for any table)
├── LLMServiceError
│   ├── LLMTimeoutError
│   └── LLMRateLimitError
└── DatabaseException
```

**Benefits**:
- ✅ Semantic error codes
- ✅ Type-safe exception handling
- ✅ Better error logging
- ✅ Easier debugging

### 4. Caching Strategy

**LLM Response Caching**:
- TTL: 5 minutes (configurable)
- Cache key: Hash of prompt + temperature
- Automatic cache invalidation

**Benefits**:
- ✅ Reduced API costs
- ✅ Faster response times
- ✅ Consistent responses

## Database Operations Migrated

### Before (Direct Supabase Access):
```python
# In API endpoints - BAD
supabase = get_supabase()

response = supabase.table("interview_sessions").insert(data).execute()
session = supabase.table("interview_sessions").select("*").eq("id", session_id).execute()

messages = supabase.table("interview_messages").select("*").eq("session_id", session_id).execute()
```

### After (Repository Pattern):
```python
# In Service Layer - GOOD
session = await self.session_repo.create_session(company_id, job_role, phase)

messages = await self.message_repo.get_session_messages(session_id, order_by="created_at")
```

## LLM Operations Migrated

### Before (Scattered Direct Calls):
```python
# In multiple API endpoints
response = llm.invoke("""You are an interviewer...""")
```

### After (Centralized LLM Service):
```python
# In Service Layer
llm_service = get_llm_service()
response = await llm_service.invoke(
    prompt=load_prompt("system", "interviewer_system.md"),
    temperature=0.7
)
```

## Prompt Externalization

### Before (Hardcoded in Python):
```python
# Direct string in code
prompt = """
You are an interviewer...
Job Role: {job_role}
Company ID: {company_id}
"""

response = llm.invoke(prompt)
```

### After (External Prompt Files):
```python
# Load from markdown files
prompt = load_prompt(
    "interview",
    "question_generation.md",
    job_role=job_role,
    phase=phase,
    difficulty_level=difficulty_level,
    previous_context=conversation_history
)

response = await llm_service.invoke(prompt, temperature=0.7)
```

### Prompt File Structure:
```
prompts/
├── system/
│   ├── interviewer_system.md    # Interviewer persona and behavior
│   ├── evaluator_system.md      # Evaluator guidelines
│   └── followup_system.md        # Follow-up generation rules
├── interview/
│   ├── question_generation.md  # Phase-appropriate question generation
│   ├── adaptive_question.md    # Adaptive follow-up questions
│   └── interview_flow.md      # Interview phase management
└── evaluation/
    ├── answer_evaluation.md    # Detailed answer evaluation
    └── scoring_rules.md        # Scoring criteria
```

## Workflow Example

### Creating a New Interview

**1. API Layer (app/api/interview.py)**:
```python
@router.post("/companies/{company_id}/interview/session")
async def start_interview(
    company_id: int,
    request: SessionStartRequest
):
    result = await interview_service.start_interview(
        company_id=request.company_id,
        job_role=request.job_role
    )
    return result
```

**2. Service Layer (app/services/interview_service.py)**:
```python
async def start_interview(self, company_id, job_role, current_phase="intro"):
    session = await self.session_repo.create_session(
        company_id=company_id,
        job_role=job_role,
        current_phase=current_phase
    )
    return {
        "session_id": session["id"],
        "current_phase": session["current_phase"],
        "question_number": session["current_question_number"]
    }
```

**3. Repository Layer (app/repositories/session_repository.py)**:
```python
async def create_session(self, company_id, job_role, current_phase="intro"):
    total_questions = 2 + 3 + 5 + 3 + 2  # All phases
    
    session_data = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "job_role": job_role,
        "status": "active",
        "current_phase": current_phase,
        "current_question_number": 0,
        "total_questions": total_questions
    }
    
    return await self.create(session_data, self._table_name)
```

### Answer Evaluation Flow

**1. API receives answer**
**2. Service evaluates using external prompt**
```python
prompt = load_prompt("evaluation", "answer_evaluation.md", ...)
evaluation = await llm_service.invoke(prompt, temperature=0.3)
```

**3. LLM Service adds caching and retry**
**4. Result returned to API**
**5. API updates database via Repository**
**6. Service updates state**
**7. API returns evaluation to client**

## Key Improvements

### 1. Maintainability
- ✅ Clear separation of concerns
- ✅ Single Responsibility Principle
- ✅ Each layer has well-defined purpose

### 2. Testability
- ✅ Repositories are easily mocked
- ✅ Services can be tested in isolation
- ✅ No tight coupling between components

### 3. Performance
- ✅ LLM caching reduces API costs
- ✅ Retry logic handles transient failures
- ✅ Async operations for non-blocking I/O

### 4. Maintainability
- ✅ External prompts are version-controlled
- ✅ Custom exceptions provide semantic errors
- ✅ Logging at each layer aids debugging

### 5. Extensibility
- ✅ Easy to add new repositories
- ✅ Simple to add new services
- ✅ Prompt changes without code deployment

## Migration Path

### API Endpoints Migration Status

**Current Status**: Endpoints still use old direct access patterns

**Next Steps**:
1. Migrate API endpoints to use `InterviewService`
2. Remove direct Supabase calls from API
3. Remove hardcoded prompts from API
4. Update error handling to use custom exceptions
5. Add tests for migrated endpoints

**Example Migration**:
```python
# BEFORE
@router.post("/companies/{company_id}/interview/session")
async def start_interview(company_id: int, data: dict):
    supabase = get_supabase()
    session_id = str(uuid.uuid4())
    
    response = supabase.table("interview_sessions").insert({
        "id": session_id,
        "company_id": company_id,
        "job_role": data.get("job_role")
    }).execute()
    
    return response.data[0]
```

```python
# AFTER
@router.post("/companies/{company_id}/interview/session")
async def start_interview(company_id: int, request: SessionStartRequest):
    result = await interview_service.start_interview(
        company_id=company_id,
        job_role=request.job_role
    )
    return result
```

## Architecture Best Practices

### DO ✅

1. **Never access database from API layer**
   ```python
   # ❌ BAD
   @router.post("/session")
   async def create(data: dict):
       response = await supabase.table("sessions").insert(data).execute()
   
   # ✅ GOOD
   @router.post("/session")
   async def create(data: dict):
       result = await service.create_session(...)
   ```

2. **Never hardcode prompts in Python**
   ```python
   # ❌ BAD
   llm.invoke("""You are an interviewer...""")
   
   # ✅ GOOD
   prompt = load_prompt("system", "interviewer_system.md", job_role=role)
   response = await llm_service.invoke(prompt)
   ```

3. **Use custom exceptions**
   ```python
   # ❌ BAD
   raise HTTPException(status_code=404, detail="Not found")
   
   # ✅ GOOD
   raise SessionNotFoundException(session_id)
   ```

4. **Always log operations**
   ```python
   # ✅ GOOD
   logger.info("Session created", extra={"session_id": session_id})
   ```

5. **Log all LLM calls with context**
   ```python
   # ✅ GOOD
   logger.info(
       "LLM invocation",
       extra={
           "prompt_length": len(prompt),
           "estimated_tokens": len(prompt) / 3,
           "temperature": temperature
       }
   )
   ```

## Next Steps

### Phase 3: API Migration

1. **Migrate interview endpoints**
   - `/companies/{company_id}/interview/session` - Create session
   - `/companies/{company_id}/interview/session/{id}` - Get session
   - `/companies/{company_id}/interview/session/{id}/next` - Get next question
   - `/companies/{company_id}/interview/answer` - Submit answer

2. **Remove old helper functions**
   - Delete `_evaluate_answer` from original API
   - Delete `_generate_phase_appropriate_question`
   - Delete `_adapt_to_performance`
   - Delete `_fade_to_conclusion`

3. **Add comprehensive tests**
   - Repository tests
   - Service tests
   - Integration tests

4. **Performance monitoring**
   - LLM token usage tracking
   - Response time monitoring
   - Cache hit ratio tracking

## Conclusion

Phase 2 refactoring successfully established a clean, maintainable architecture with:

- ✅ Repository pattern for database abstraction
- ✅ Service layer containing business logic
- ✅ Centralized LLM management with caching
- ✅ External prompt template system
- ✅ Comprehensive error handling
- ✅ Clear 5-layer architecture

The foundation is now solid. Follow the migration path in Phase 3 to complete the refactoring of API endpoints and enjoy a more maintainable, testable, and performant codebase.