# AI Interview Agent - Architecture Refactor V2

## Overview
Two independent LangGraph workflows replacing the single monolithic loop. Each matches an HTTP request precisely.

---

## Files Used (API Route: `app/api/interview_agent.py`)

### 1. API Layer
| File | Role |
|------|------|
| `app/api/interview_agent.py` | REST endpoints (`/interviews/{id}/questions/next`, `/interviews/{id}/answers`) |

### 2. Graph Workflows (New)
| File | Role |
|------|------|
| `app/graph/question_workflow.py` | Question generation graph (session_init → company_context → question_generation → END) |
| `app/graph/evaluation_workflow.py` | Answer evaluation graph (answer_evaluator → decision → END) |

### 3. Graph State
| File | Role |
|------|------|
| `app/graph/interview_state.py` | Shared TypedDict state for both workflows |

### 4. Orchestrator
| File | Role |
|------|------|
| `app/orchestrators/interview_orchestrator.py` | Coordinates API requests with correct LangGraph workflow |

### 5. Agent Nodes
| File | Role |
|------|------|
| `app/agents/session_init_node.py` | Initializes session metadata |
| `app/agents/company_context_node.py` | Retrieves company RAG context (synchronous) |
| `app/agents/question_generation_node.py` | Generates one question via LLM; increments `question_number` |
| `app/agents/answer_evaluator_node.py` | Evaluates answer; strips markdown JSON fences; logs raw response |
| `app/agents/decision_node.py` | Decides next action; handles `evaluation_failed` flag |

### 6. Services
| File | Role |
|------|------|
| `app/services/llm_service.py` | LLM invocation (`invoke`) |
| `app/services/prompt_loader.py` | Loads prompt templates from filesystem |

### 7. Repositories
| File | Role |
|------|------|
| `app/services/repositories.py` | Instantiates session & message repos |
| `app/repositories/session_repository.py` | Session CRUD |
| `app/repositories/message_repository.py` | Message/evaluation CRUD |

### 8. RAG (Pinecone)
| File | Role |
|------|------|
| `app/rag/pinecone_store.py` | Pinecone retriever (`get_company_retriever`) |

### 9. Exceptions
| File | Role |
|------|------|
| `app/exceptions.py` | `SessionNotFoundException` |

---

## Workflow Diagrams

### Workflow 1: Question Generation
```
POST /interviews/{session_id}/questions/next
            │
            ▼
    session_init_node
            │
            ▼
    company_context_node   ← Pinecone retriever.invoke (synchronous)
            │
            ▼
    question_generation_node  ← LLM generates 1 question
            │
            ▼
          END
```
*Never calls evaluator, decision, or question-loop.*

### Workflow 2: Answer Evaluation
```
POST /interviews/{session_id}/answers
            │
            ▼
    answer_evaluator_node   ← LLM evaluates, strips markdown JSON
            │
            ▼
    decision_node           ← decide continue/finish
            │
            ▼
          END
```
*Never generates a new question itself.*

---

## State: `InterviewState`

```python
class InterviewState(TypedDict, total=False):
    session_id: str
    company_id: int
    candidate_id: str
    job_role: str
    interview_type: str
    current_phase: str
    question_number: int
    total_questions: int
    current_question: str
    candidate_answer: str
    difficulty_level: int
    conversation_history: list
    company_context: list
    company_requirements: str
    evaluation_score: float
    technical_score: float
    communication_score: float
    strengths: list
    weaknesses: list
    feedback_detail: str
    evaluation_failed: bool
    next_action: str
    is_complete: bool
    final_report: dict
```

---

## Endpoint Behaviour

### `POST /interviews/{session_id}/questions/next`
1. Receive phase, conversation_history, question_number, difficulty from frontend.
2. Load session from DB.
3. Build `InterviewState` with `question_number` = current.
4. Execute **Question Workflow** (`question_workflow.ainvoke`).
5. Return generated question, new `question_number`, `phase`, `difficulty_level`.

### `POST /interviews/{session_id}/answers`
1. Receive `question`, `candidate_answer`, `conversation_history`, etc.
2. Load session from DB.
3. Build `InterviewState` with `candidate_answer` and `current_question`.
4. Execute **Evaluation Workflow** (`evaluation_workflow.ainvoke`).
5. Return `evaluation` (score, technical, communication, strengths, weaknesses, feedback) and `next_action`.

---

## Fixes in This Version

| Fix | Detail |
|-----|--------|
| **Increment question_number** | `question_generation_node` now sets `question_number = question_number + 1` in state. |
| **Evaluator JSON cleaning** | Removes \`\`\`json fences; logs raw response; avoids silent fallback to 7.0. |
| **Decision evaluator fail** | If `evaluation_failed == True`, `next_action = 'finish'` to break loop. |
| **Company context await fix** | Pinecone retriever is synchronous → uses `retriever.invoke()` (no `await`). |
| **Two separate graphs** | No more GraphRecursionError or question-generation inside evaluation. |
| **Orchestrator uses correct graph** | Question generation calls question graph; evaluation calls evaluation graph. |