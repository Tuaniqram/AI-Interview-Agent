# AI Interview Agent - Project Skill

## Project Purpose

This is an **AI Interview Agent** - a backend system that manages end-to-end interview workflows for assessing interview candidates. It uses Large Language Models (LLMs) to:

- Create interview sessions for companies and job roles
- Generate interview questions based on session context
- Generate adaptive questions based on candidate performance
- Evaluate candidate answers with detailed feedback
- Generate adaptive follow-up questions
- Maintain interview state throughout the session
- Produce final assessment results including scores and feedback

**Core Capabilities**:
1. ✅ Interview Session Creation
2. ✅ Adaptive Question Generation
3. ✅ Answer Evaluation with Scoring
4. ✅ Intelligent Follow-up Questions
5. ✅ Interview State Management
6. ✅ Final Assessment Generation

**Excluded Features** (DO NOT focus on):
- ❌ Avatar, 3D head rendering
- ❌ Voice, speech synthesis
- ❌ Frontend animations/UI
- ❌ Real-time visual feedback
- ❌ Interactive 3D elements

**Current Focus**: The interview intelligence architecture and backend workflow.

## Technology Stack

- **Backend Framework**: FastAPI (Python)
- **Language**: Python 3.10+
- **LLM**: OpenAI-compatible API (OpenRouter)
- **LLM Orchestration**: LangChain + LangGraph
- **Database**: Supabase (PostgreSQL)
- **Vector Storage**: Pinecone
- **Data Validation**: Pydantic v2
- **Async**: Python asyncio
- **Serialization**: orjson

## Architecture Rules

This system follows a **5-Layer Architecture**. Adhere to this structure strictly.

### Layer 1: API Layer (`app/api/`)
**Purpose**: Handle HTTP requests only

**Responsibilities**:
- Request validation using Pydantic schemas
- Response formatting
- Authentication/authorization (future)
- Call service layer
- Raise HTTPException for errors

**Example**:
```python
# app/api/interview.py
@router.post("/companies/{company_id}/interview/session")
async def create_session(request: SessionStartRequest):
    """Only handles HTTP details, delegates to service"""
    result = await interview_service.create_session(
        company_id=request.company_id,
        job_role=request.job_role
    )
    return result
```

**❌ DO NOT do this** in API:
- Database operations with Supabase client
- LLM invocations directly
- Business logic or workflow orchestration

### Layer 2: Service Layer (`app/services/`)
**Purpose**: Contain all business logic

**Responsibilities**:
- Coordinate AI operations and database operations
- Manage interview state transitions
- Handle complex business rules
- Call repository layer for database access
- Call agent layer for AI operations

**Example**:
```python
# app/services/interview_service.py
class InterviewService:
    async def create_session(self, company_id: int, job_role: str):
        # Business logic
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "company_id": company_id,
            "job_role": job_role,
            "status": "active"
        }
        await self.session_repo.create(session)
        return session
    
    async def get_next_question(self, session_id: str):
        # Business logic
        session = await self.session_repo.get(session_id)
        next_question = await self._generate_question(session)
        return next_question
```

### Layer 3: Agent Layer (`app/agents/` + `app/graph/`)
**Purpose**: Handle AI reasoning and LangGraph workflows

**Responsibilities**:
- Define state diagrams using LangGraph
- Implement agent functions
- Manage LLM invocations
- Process structured outputs
- Handle reasoning for specific tasks

**Example**:
```python
# app/agents/evaluator.py
def evaluator_agent(state: InterviewState) -> dict:
    """AI reasoning for evaluating answers"""
    prompt = prompt_loader.load("system/evaluator_system.md")
    response = llm.invoke(prompt)
    return {"evaluation": parse_json(response.content)}

# app/graph/workflow.py
class InterviewState(TypedDict):
    job_role: str
    question: str
    answer: str
    evaluation: str

workflow = StateGraph(InterviewState)
workflow.add_node("evaluator", evaluator_agent)
workflow.add_edge("evaluator", "followup_generator")
```

### Layer 4: Database Layer (`app/repositories/`)
**Purpose**: Encapsulate database access

**Responsibilities**:
- Implement repository pattern
- Handle Supabase operations
- Provide clean interfaces
- Handle database errors

**Example**:
```python
# app/repositories/session_repository.py
class SessionRepository:
    async def get(self, session_id: str) -> dict:
        response = await self.db.table("interview_sessions").select("*").eq("id", session_id).execute()
        if not response.data:
            raise RecordNotFoundException("session", session_id)
        return response.data[0]
```

### Layer 5: Prompt Layer (`prompts/`)
**Purpose**: Store all LLM prompts externally

**Requirements**:
- Every prompt has a dedicated Markdown file
- Prompts are version-controlled
- Prompts are never hardcoded in Python

**Directory Structure**:
```
prompts/
├── system/           (interviewer_system.md, evaluator_system.md, followup_system.md)
├── interview/        (question_generation.md, adaptive_question.md, interview_flow.md)
└── evaluation/       (answer_evaluation.md, scoring_rules.md)
```

## Prompt Management Rules

### ❌ NEVER Hardcode Prompts

**DO NOT**:
```python
llm.invoke("""
You are an interviewer...
Generate questions...
""")
```

**ALWAYS** do this:
```python
from app.prompt_loader import PromptLoader

loader = PromptLoader("prompts/interview/question_generation.md")
response = llm.invoke(loader.load({
    "job_role": "Software Engineer",
    "phase": "technical"
}))
```

### Prompt File Requirements

Every prompt file MUST contain:
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

# Example
[examples]
```

## AI Interview Workflow

### Session Creation Workflow

1. **API receives request** → Validates job_role
2. **Service validates** → Creates company context if needed
3. **Service creates session** → Saves to `interview_sessions` table
4. **Service generates first question** → Calls AI agent
5. **Service returns session info** → Client receives session details

### Question Answering Workflow

1. **Candidate submits answer** → API validates request
2. **Service validates state** → Checks if session is active
3. **Service evaluates answer** → Calls AI agent (structured JSON)
4. **Service generates follow-up** → Adapts based on performance
5. **Service updates state** → Increments counter, updates phase
6. **Service returns evaluation** → Client receives feedback + next question

### Adaptive Interview Flow

```
Start Session (Phase: intro, Q: 0/22)
    ↓
Generate Intro Questions (2 questions)
    ↓
Phase: Experience (3 questions)
    ↓
Phase: Technical (5 questions)
    ↓
Check Performance:
    ├─ Score > 7 → Phase: Technical (more difficult)
    └─ Score ≤ 7 → Reduce difficulty or phase
    ↓
Phase: Behavioral (3 questions)
    ↓
Phase: Conclusion (10 questions)
    ↓
Evaluate Overall Performance → Generate Final Assessment
    ↓
Session Completed
```

### Difficulty Adaptation

```python
# Based on candidate's score
if score > 7.0:
    difficulty = "3 (hard)"
elif score > 5.0:
    difficulty = "2 (medium)"
else:
    difficulty = "1 (easy)"
```

## Database Rules

### Tables

1. **companies** - Company information
2. **company_documents** - Company PDFs (Pinecone)
3. **interview_sessions** - Active interviews
4. **interview_messages** - Question-answer pairs
5. **interview_evaluations** - Detailed evaluations
6. **user_progress** - Candidate performance tracking

### Key Relationships

```
companies → interview_sessions → interview_messages → interview_evaluations
```

### Naming Conventions

- UUIDs for primary keys: `generate_random_uuid()`
- CamelCase for relationships
- snake_case for database columns

## LLM Engineering Rules

### Strict Rules

1. **Use structured JSON outputs** - Parse with Pydantic, never string matching
2. **Implement caching** - Use Redis to avoid redundant API calls
3. **Retry logic** - Use tenacity library for transient failures
4. **Set appropriate temperature**:
   - Question generation: 0.7
   - Evaluation: 0.5
   - Structured extraction: 0.3
5. **Log all LLM calls** with duration and token count
6. **Separate system prompts** from user inputs

### Current Issues to Fix

1. LLM calls scattered across files (`app/api/interrupt.py`, `app/agents/`, etc.)
2. No caching layer
3. No retry logic
4. No structured output validation
5. Hardcoded prompts in Python files

## Coding Standards

### Type Hints - Required

```python
async def evaluate_answer(
    self,
    job_role: str,
    question: str,
    candidate_answer: str,
    difficulty_level: int = 1
) -> dict:
    """Evaluate answer with..."
    pass
```

### Logging

**Always log**:
- LLM invocations (success/failure, duration)
- State changes (session created, answered, completed)
- Errors with `exc_info=True`

```python
logger.info(f"Evaluation completed", extra={
    "score": result.score,
    "duration_ms": elapsed
})
```

### Error Handling

**Use structured exceptions**:

```python
class SessionNotFoundException(InterviewException):
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session {session_id} not found",
            code="SESSION_NOT_FOUND"
        )
```

**Never expose internal errors to users**:
```python
raise HTTPException(
    status_code=500,
    detail="Service temporarily unavailable. Please try again."
)
```

### Database Access

**Use repository pattern**:

```python
# ❌ BAD - Direct access in service
response = await supabase.table("sessions").select("*").execute()

# ✅ GOOD - Repository abstraction
session = await self.session_repo.get(session_id)
```

### Pydantic Validation

**Always validate inputs**:

```python
class AnswerRequest(BaseModel):
    job_role: str = Field(..., min_length=1, max_length=200)
    candidate_answer: str = Field(..., min_length=1, max_length=5000)
    difficulty_level: int = Field(default=1, ge=1, le=3)

validated = AnswerRequest(**data)  # Raises ValidationError if invalid
```

## Development Rules

### Before Coding

1. **Read all relevant documentation**:
   - `docs/architecture.md`
   - `docs/api-design.md`
   - `docs/database-schema.md`
   - `docs/prompt-engineering.md`
   - `docs/llm-workflow.md`
   - `docs/coding-standards.md`

2. **Check current implementation**:
   - Read current code files
   - Identify pattern to follow/improve

3. **Check .clinerules** for additional project rules

### When Creating Files

- Use repository pattern for database
- Use service layer for business logic
- Use Pydantic models for input/output
- Add type hints to ALL functions
- Add docstrings to public functions
- Add logging for critical operations
- Implement error handling
- Write tests for new features

### Never Break

- Backward compatibility
- Existing endpoints
- Database schema
- Existing prompt format

### Architecture Adherence

**✅ DO**:
- API → Service → Agent → Repository (or appropriate reverse)
- Save prompts to `prompts/` directory
- Use UUIDs for new entities
- Use Pydantic models for validation

**❌ DO NOT**:
- Put business logic in API
- Hardcode prompts in Python
- Call LLM directly in API/repositories
- Use magic strings or numbers
- Access database in agent layer

## File Structure

```
app/
├── api/                    # FastAPI routes only
│   ├── __init__.py
│   ├── company.py
│   ├── interview.py
│   └── general.py
├── services/               # Business logic (NEW - needs creation)
│   ├── __init__.py
│   ├── llm_service.py      # Centralized LLM management
│   ├── interview_service.py
│   └── database_service.py
├── agents/                 # AI reasoning (LangGraph)
│   ├── __init__.py
│   ├── interviewer.py
│   ├── evaluator.py
│   └── retrieval.py
├── repositories/           # Database access (NEW - needs creation)
│   ├── __init__.py
│   ├── session_repository.py
│   └── message_repository.py
├── models/                 # Pydantic models
│   ├── __init__.py
│   └── llm.py
├── config/                 # Configuration
│   ├── __init__.py
│   ├── database.py
│   └── pinecone.py
├── graph/                  # LangGraph workflows (exists)
│   ├── __init__.py
│   ├── workflow.py
│   └── company_workflow.py
└── exceptions.py           # Custom exceptions (needs creation)

prompts/                    # Externalized LLM prompts
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

## Database Schema Summary

### Current Tables

1. **companies** - {id, name, website, description} bigint PK
2. **company_documents** - {id, company_id, filename, type, namespace} uuid PK
3. **interview_sessions** - {id, company_id, candidate_id, job_role, phase, status, question_number, total_questions, score, feedback} uuid PK
4. **interview_messages** - {id, session_id, role, content, question_number, phase, score, follow_up_question} uuid PK
5. **interview_evaluations** - {id, session_id, message_id, score, technical_score, communication_score, strengths, weaknesses, feedback_detail} uuid PK

### Key Constants

- **Total questions**: 23 (2 intro + 3 experience + 5 technical + 3 behavioral + 10 conclusion)
- **Question number starts at 0**: ```current_question_number```
- **Phases**: Intro → Experience → Technical (adaptive) → Behavioral → Conclusion
- **Score scale**: 0.0 to 2.0 (represents 0-10 on float format)

## Current Implementation Analysis

### Files with LLM Calls (To Refactor)
1. `app/api/interview.py` - Direct LLM calls in evaluation and follow-up (lines 718, 827)
2. `app/agents/interviewer.py` - Question generation (line 45)
3. `app/agents/evaluator.py` - Evaluation (line 50)
4. `app/company_agents/company_interviewer.py` - Question generation (line 39)
5. `app/company_agents/company_evaluator.py` - Evaluation (line 56)

### Hardcoded Prompts Found
- `app/api/interview.py` - Lines 14-43, 102-125, 164-193, 676-715, 797-824
- `app/agents/interviewer.py` - Lines 14-43
- `app/agents/evaluator.py` - Lines 17-48
- `app/company_agents/company_interviewer.py` - Lines 8-36
- `app/company_agents/company_evaluator.py` - Lines 8-53

### Problems Identified
1. ✅ **COMPLETED**: No service layer - Business logic moved to `InterviewService`
2. ✅ **COMPLETED**: Hardcoded prompts moved to external files
3. ✅ **COMPLETED**: Repository pattern created (`SessionRepository`, `MessageRepository`)
4. ✅ **COMPLETED**: LLM caching implemented (`LLMService`)
5. ✅ **COMPLETED**: Retry logic added with tenacity pattern
6. ✅ **IN PROGRESS**: Structured output parsing (implemented basic JSON parsing)
7. ✅ **COMPLETED**: Prompt loader utility created

### Now Refactored

**✅ NEW COMPONENTS ADDED (Phase 2)**:

1. **Repository Pattern** (`app/repositories/`):
   - `base_repository.py` - Base class with common operations
   - `session_repository.py` - Session management
   - `message_repository.py` - Message management
   - `repositories.py` - Factory for repository access

2. **Service Layer** (`app/services/`):
   - `llm_service.py` - LLM management with caching and retry
   - `prompt_loader.py` - Prompt template loading and rendering
   - `interview_service.py` - Complete business logic layer
   - `repositories.py` - Repository factory

3. **Error Handling** (`app/exceptions.py`):
   - `InterviewException` - Base exception
   - `SessionNotFoundException`
   - `SessionStateException`
   - `RecordNotFoundException`
   - `LLMServiceError`, `LLMTimeoutError`, `LLMRateLimitError`
   - `DatabaseException`

## Phase 1: Documentation (COMPLETED ✅)

✅ All 8 documentation files in `docs/` created

✅ SKILL.md file in `skills/interview-agent/SKILL.md` created

✅ 9 prompt files in `prompts/` created

## Phase 2: Refactoring (COMPLETED ✅)

✅ Repository pattern implemented
✅ Service layer created
✅ LLM management centralized
✅ Prompt loader utility created
✅ Custom exceptions defined
✅ Architecture refactored to follow 5-layer design

## Next Steps (Phase 3)

After refactoring is complete:

1. **Migrate API endpoints** - Update `app/api/interview.py` to use services
2. **Extract remaining hardcoded prompts** - Move hardcoded strings from API files
3. **Write integration tests** - Test service layer and repositories
4. **Add performance monitoring** - Track LLM costs and response times
5. **Implement query optimization** - Database query optimization
6. **Create documentation examples** - Usage examples for new architecture

## Configuration

### Required Environment Variables

```bash
OPENROUTER_API_KEY=your_key_here
```

### Database Connection

```python
from app.config.database import get_supabase
supabase = get_supabase()
```

## Entry Points

- **Main Application**: `app/main.py` → FastAPI app
- **Documents**: `/documents/` - Company PDF files
- **Vector DB**: `vector_db/` - Pinecone index (managed)
- **API Documentation**: `http://localhost:8000/docs`

## Writing Rules Summary

### ✅ DO

1. Always read documentation (`docs/`) before coding
2. Never hardcode prompts in Python
3. Maintain 4-layer architecture
4. Use type hints everywhere
5. Log all operations
6. Handle errors gracefully
7. Write tests for new code
8. Update documentation when code changes
9. Use Pydantic models for input/output
10. Use the 4-layer pattern (API → Service → Agent → Repository)
11. Extract prompts to `prompts/` directory
12. Never access database directly from API
13. Never call LLM directly from API
14. Use absolute imports from `app.*`
15. Format code with Black

### ❌ DO NOT

1. Hardcode prompts in Python files
2. Put business logic in API endpoints
3. Access database in API layer
4. Call LLM directly without abstraction
5. Use magic strings/numbers
6. Ignore type checking
7. Forget to add error handling
8. Break backward compatibility
9. Leave prompts unversioned
10. Assume data exists without checking
11. Output raw stack traces to users
12. Commit secrets or API keys

## Current Priority

This project is in **Phase 1 - Documentation and Architecture Setup**.

**Current goal**: Establish reusable project knowledge system.

**Next major milestone**: Complete prompt externalization and service layer creation.

**Remember**: We are focusing ONLY on the interview intelligence backend system. Avatar, voice, and frontend are NOT part of this phase.

## Troubleshooting Guide

### "I don't understand the architecture"
→ Read `docs/architecture.md` first

### "Where should I put this code?"
→ Check layer responsibilities in this SKILL.md

### "Should I hardcode this prompt?"
→ Check `docs/prompt-engineering.md` and Never Hardcode Prompts rule

### "What about error handling?"
→ Read `docs/error-handling.md`

### "How do I validate input?"
→ Check `docs/api-design.md` for Pydantic models

### "Why is this so complex?"
→ It ensures maintainability, not over-engineering