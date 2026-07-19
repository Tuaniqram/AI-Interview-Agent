# AI Interview Agent - Architecture

## Overview

The AI Interview Agent is a backend system that manages end-to-end interview workflows for assessing interview candidates. It integrates with AI language models, vector databases, and relational databases to provide intelligent interview management.

## Current Architecture Issues

### ❌ Problems Found

1. **No Service Layer**
   - Business logic is scattered across API endpoints
   - Direct database operations in `app/api/interview.py`
   - Missing separation of concerns between HTTP handling and business logic

2. **Hardcoded Prompts**
   - All LLM prompts embedded directly in Python files
   - Violates prompt management rules
   - Difficult to maintain, version-control, and iterate

3. **Loose Type Hints**
   - Limited use of Pydantic schemas
   - Primitive types used in return values
   - No type safety for external API contracts

4. **Direct LLM Integration**
   - No caching layer
   - No structured output validation
   - No retry logic in place

5. **Direct Database Access**
   - API endpoints directly call Supabase
   - No repository pattern
   - Error handling is inconsistent

## Recommended Architecture (4-Layer Pattern)

### Layer 1: API Layer (`app/api/`)

**Purpose**: Handle HTTP requests only

**Responsibilities**:
- Request validation using Pydantic schemas
- Response formatting
- Authentication/authorization
- Call service layer
- Exception handling (HTTPException)

**Do NOT do this**:
```python
# ❌ BAD - Business logic in API
def get_next_question(company_id, session_id):
    response = supabase.table("interview_sessions").select("*").execute()
    # Complex business logic here...
    return result
```

**Do this**:
```python
# ✅ GOOD - API only
def get_next_question(company_id: int, session_id: str):
    question = interview_service.get_next_question(
        company_id=company_id,
        session_id=session_id
    )
    return question
```

### Layer 2: Service Layer (`app/services/`)

**Purpose**: Contain business logic and workflow execution

**Responsibilities**:
- Coordinate AI operations and database operations
- Manage interview state transitions
- Handle complex business rules
- Call repository layer for database access
- Call agent layer for AI operations

**Example Service**:
```python
# app/services/interview_service.py
class InterviewService:
    def get_next_question(self, company_id, session_id):
        # Business logic
        session = self.session_repo.get(session_id)
        phase = session.current_phase
        
        # Adapt difficulty based on performance
        difficulty = self._calculate_difficulty(session)
        
        # Generate question (may use AI)
        question = self._generate_question(phase, difficulty)
        
        # Update state
        session.current_question_number += 1
        self.session_repo.update(session)
        
        return question
```

### Layer 3: Agent Layer (`app/agents/` + `app/graph/`)

**Purpose**: Handle AI reasoning and LangGraph workflows

**Responsibilities**:
- Define state diagrams using LangGraph
- Implement agent functions
- Manage LLM invocations
- Process structured outputs
- Handle reasoning for specific tasks (interview, evaluation, retrieval)

**Example Agent**:
```python
# app/agents/question_generator.py
def question_generator(state: InterviewState) -> dict:
    # AI reasoning
    prompt = prompt_loader.load("interview/question_generation.md")
    response = llm.invoke(prompt, temperature=0.7)
    
    # Parse structured output
    question_data = parse_json_response(response.content)
    
    return {
        "question": question_data["question"],
        "category": question_data["category"]
    }
```

```python
# app/graph/interview_workflow.py
from langgraph.graph import StateGraph
from typing import TypedDict

class InterviewState(TypedDict):
    job_role: str
    company_context: str
    question: str
    answer: str
    evaluation: str

workflow = StateGraph(InterviewState)
workflow.add_node("question_generator", question_generator)
workflow.add_node("evaluator", evaluator_agent)
workflow.set_entry_point("question_generator")
workflow.add_edge("question_generator", "evaluator")
graph = workflow.compile()
```

### Layer 4: Database Layer (`app/repositories/`)

**Purpose**: Handle database access and operations

**Responsibilities**:
- Encapsulate Supabase operations
- Implement repository pattern
- Handle database errors
- Provide clean interfaces for services

**Example Repository**:
```python
# app/repositories/session_repository.py
class SessionRepository:
    def __init__(self, db):
        self.db = db
    
    def get(self, session_id: str) -> dict:
        response = self.db.table("interview_sessions").select("*").eq("id", session_id).execute()
        if not response.data:
            raise SessionNotFoundError(session_id)
        return response.data[0]
    
    def save(self, session_data: dict) -> dict:
        response = self.db.table("interview_sessions").insert(session_data).execute()
        return response.data[0]
    
    def update(self, session_id: str, updates: dict) -> dict:
        response = self.db.table("interview_sessions").update(updates).eq("id", session_id).execute()
        return response.data[0]
```

### Layer 5: Prompt Layer (`prompts/`)

**Purpose**: Store all LLM prompts externally

**Responsibilities**:
- Version-controlled prompt files
- Documentation of each prompt's purpose
- Clear input/output specifications
- Keep prompts out of code

**Do NOT do this**:
```python
# ❌ BAD - Hardcoded prompt
llm.invoke("""
You are an interviewer...
Generate questions...
""")
```

**Do this**:
```python
# ✅ GOOD - Load prompt from file
from prompts.load import PromptLoader

loader = PromptLoader("prompts/interview/question_generation.md")
prompt = loader.load({
    "job_role": state.job_role,
    "difficulty": state.difficulty
})
response = llm.invoke(prompt)
```

## Current vs Recommended Separation

| Current | Recommended |
|---------|------------|
| API endpoints contain business logic | Business logic in service layer |
| Direct Supabase calls in API | Database operations in repository layer |
| Hardcoded prompts | Externalized prompt files |
| Direct LLM invocation | Agent layer with caching/retry |
| T.TypedDict for state | Clear state schemas with Pydantic |
| Limited type safety | Full type safety with Pydantic models |

## Integration Points

### LLM Integration
- **Current**: Direct `llm.invoke()` calls in various files
- **Recommended**: Single LLM manager in `app/services/llm_manager.py` with caching and retry logic

### Database Integration  
- **Current**: Direct `supabase.table().select()` calls
- **Recommended**: Repository pattern with `SessionRepository`, `MessageRepository`, etc.

### Vector Database Integration
- **Current**: Pinecone store exists but not integrated in main interview flow
- **Recommended**: Integration when generating company-specific questions

## Technology Stack

- **Backend**: FastAPI (Web framework)
- **Python**: 3.x (Language)
- **LLM**: OpenAI-compatible API (via LangChain)
- **Orchestration**: LangGraph + LangChain
- **Database**: Supabase (PostgreSQL)
- **Vector Storage**: Pinecone
- **Validation**: Pydantic v2
- **Async**: Python asyncio
- **Logging**: Python logging module

## Key Workflows

### Interview Creation Workflow
1. API endpoint receives request
2. Service validates input
3. Service creates session in DB
4. Service generates first question
5. Service returns session details

### Interview Execution Workflow
1. Candidate submits answer via API
2. API validates request
3. Service evaluates answer
4. Service generates adaptive follow-up
5. Service updates session state
6. Service returns evaluation + next question

### Interview Completion Workflow
1. Service detects completion condition
2. Service calculates final score
3. Service generates final feedback
4. Service updates session to "completed"
5. Service returns final assessment