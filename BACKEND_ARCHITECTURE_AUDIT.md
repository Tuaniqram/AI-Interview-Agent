# 🚨 BACKEND ARCHITECTURE AUDIT REPORT

**Date:** 2026-07-19
**Status:** ❌ FAIL — 7/7 Categories Have Critical Issues

---

## Executive Summary

The architecture is **split into two incompatible code paths** that serve different API styles, use different data models, and neither is fully wired to the frontend. The project has suffered from incomplete refactoring: the new LangGraph architecture exists in parallel with the old service-layer architecture, creating a fragmented system where no single path works end-to-end.

---

## Phase 1: API Layer — ❌ FAIL

### Duplicate API Routers Registered

**Problem:** Two entirely separate API routers are both registered in `app/main.py`:

| File | Route Prefix | Engine |
|------|-------------|--------|
| `app/api/interview_agent.py` | `/api/interviews/...` | LangGraph + Orchestrator |
| `app/api/interview.py` | `/companies/{company_id}/interview/...` | Old InterviewService |

Both are included via `app.include_router()` in `main.py`.

**File:** `app/main.py`, lines 35-37
```python
app.include_router(interview_router)      # OLD: app/api/interview.py
app.include_router(interview_agent)       # NEW: app/api/interview_agent.py
```

**Recommended fix:** Remove one router. If LangGraph is the target architecture, remove `app/api/interview.py` and delete its `include_router()` call from `main.py`.

### Missing Endpoints in New LangGraph API

The architecture document specifies 5 endpoints for `app/api/interview_agent.py`:

| Endpoint | Exists? | Status |
|----------|---------|--------|
| `POST /api/interviews` | ✅ Yes | |
| `POST /api/interviews/{session_id}/questions/next` | ✅ Yes | |
| `POST /api/interviews/{session_id}/answers` | ✅ Yes | |
| `GET /api/interviews/{session_id}/status` | ✅ Yes | |
| `GET /api/interviews/{session_id}/summary` | ✅ Yes | |
| `GET /api/interviews/{session_id}/rag-status` | ❌ **MISSING** | Not implemented |

**File:** `app/api/interview_agent.py`
**Issue:** Missing rag-status endpoint that the architecture document requires.

### Route Inconsistency: `/api/` Prefix vs Root

The architecture documents show bare routes like `POST /interviews` but implementation prefixes them with `/api/`.

### Old API Uses Wrong Data Flow

The old `app/api/interview.py` calls `InterviewService` directly instead of going through the orchestrator. It bypasses the entire LangGraph architecture.

**File:** `app/api/interview.py`, lines 78-82
```python
result = await interview_service.start_interview(
    company_id=company_id,
    job_role=request.job_role,
```
This calls `app/services/interview_service.py` directly — no LangGraph, no orchestrator.

---

## Phase 2: Orchestrator Layer — ❌ FAIL

### Orchestrator Only Serves New API, Not Old One

**Problem:** The orchestrator `app/orchestrators/interview_orchestrator.py` only services routes from `app/api/interview_agent.py`. The old `app/api/interview.py` completely bypasses the orchestrator and calls `InterviewService` directly.

### State Construction Issues

The orchestrator creates `InterviewState` and passes it to LangGraph workflows. However, the `InterviewState` model requires many fields (`messages`, `company_context`, `current_phase`, etc.) and there is no validation that all required fields are populated before invoking the workflow.

**File:** `app/orchestrators/interview_orchestrator.py` — Missing field validation before workflow invocation.

### No Session State Recovery on Error

If a LangGraph workflow fails mid-execution, there is no mechanism to recover the session state. The session may be left in an inconsistent state.

---

## Phase 3: LangGraph Workflow — ❌ FAIL

### Question Workflow: Missing Error Paths

**File:** `app/graph/question_workflow.py`

Nodes are connected correctly:
```
session_init → company_context → question_generation
```
But there is no error handling node. If `company_context` fails (e.g., Pinecone unavailable), the workflow crashes with no fallback path.

### Evaluation Workflow: Missing Edge from Decision

**File:** `app/graph/evaluation_workflow.py`

```
answer_evaluator → decision
```

The `decision` node determines next actions (continue, complete, phase_change) but these decisions are **not acted upon** in the workflow graph itself. The decision is returned as data but no conditional edges route to different next states based on the decision.

### Evaluation Not Saved to Dedicated Table

The evaluation workflow saves results to `interview_messages` table with a `score` field, but the database schema has a dedicated `interview_evaluations` table that is **never used**.

**File:** `app/agents/answer_evaluator_node.py` — saves to messages, not evaluations.
**File:** `database_schema.sql` — `interview_evaluations` table exists but has no repository.

### Main Workflow Not Wired

**File:** `app/graph/interview_workflow.py` — This file exists but is unclear if it's actively used. The orchestrator calls `question_workflow` and `evaluation_workflow` directly as separate workflows rather than through a unified main workflow.

---

## Phase 4: Company RAG Context — ⚠️ FAIL (Incomplete)

### RAG Integration Exists but Fragile

**File:** `app/agents/company_context_node.py`

The node correctly:
1. Takes `company_id` from state
2. Constructs Pinecone namespace as `company_{company_id}`
3. Uses `PineconeVectorStore` retriever
4. Returns `company_context` with retrieved documents

**Problem A — No Fallback:**
If no documents have been uploaded for a company, the Pinecone namespace `company_{company_id}` won't exist. The node has **no fallback** to gracefully handle missing company context. The interview may crash or proceed without context.

**Problem B — Question Prompt Not Guaranteed to Use Context:**
**File:** `app/agents/question_generation_node.py`

The prompt template includes `{company_requirements}` but if the context is empty (no docs found), the LLM still generates a question — without company context. The architecture requires EVERY company interview question to reference company context, but there's no guard to verify this.

**Problem C — `company_id` Propagation:**
The old API (`app/api/interview.py`) takes `company_id` as a path parameter. The new API (`app/api/interview_agent.py`) accepts `company_id` in the request body for `POST /api/interviews`. But the frontend service only sends `company_id` as a path parameter in the URL, not as body data. If the frontend connects to the new API, `company_id` may not be available in the InterviewState.

---

## Phase 5: AI Question Generation — ⚠️ FAIL (Partial)

### Hardcoded Fallback Questions Exist

**File:** `app/agents/question_generation_node.py`

The node has **hardcoded fallback questions** when the LLM call fails:

```python
# Example logic found:
if not ai_question:
    return {"question": "Tell me about your experience with..."}
```

**Architecture mandate:** "NO hardcoded questions, NO templates, ALWAYS use LLM."

This is a direct violation. While the fallback may be intended for resilience, it breaks the architecture rule.

### Prompt Loading Path Issue

**File:** `app/services/prompt_loader.py`

The prompt loader constructs paths like `prompts/interview/question_generation.md`. This works when running from project root. However, if the application is started from a different working directory (e.g., via Docker), the relative path will break.

### LLM Service Is Correctly Used

**File:** `app/services/llm_service.py`
✅ Properly wraps `ChatOpenAI`/`AzureChatOpenAI` from `app/models/llm.py`
✅ All agent nodes use this service instead of calling `llm.invoke()` directly
✅ Uses configurable model settings

---

## Phase 6: Database Layer — ❌ FAIL

### Orphaned `interview_evaluations` Table

**File:** `database_schema.sql` — Has `interview_evaluations` table.
**File:** `app/repositories/` — No `evaluation_repository.py` exists.

The `interview_evaluations` table has:
- `session_id` FK → `interview_sessions`
- `message_id` FK → `interview_messages`
- Structured fields: `technical_score`, `communication_score`, `strengths`, `weaknesses`

But no code writes to or reads from this table. Evaluations are stored as inline `score` fields in `interview_messages`.

### `create_question` Has Inverted Fields

**File:** `app/repositories/message_repository.py`, lines 98-118

```python
async def create_question(self, session_id, question_text, question_number, phase):
    return await self.create_message(
        ...
        message_type=question_text,  # ❌ BUG: question text stored in message_type, not content
        content="",                   # ❌ BUG: content is empty
        ...
    )
```

The `question_text` is stored in the `message_type` column and `content` is empty string. This is a **data corruption bug** — questions will not be retrievable properly.

### Missing Repositories for User Progress

**File:** `database_schema.sql` — Has `user_progress` table.
**File:** `app/repositories/` — No repository for `user_progress`.

The `user_progress` table tracks candidate progress across sessions but is completely unused by the backend code.

### Hardcoded Question Counts

**File:** `app/repositories/session_repository.py`, lines 53-59

```python
total_questions = (
    2 +  # intro
    3 +  # experience
    5 +  # technical
    3 +  # behavioral
    2    # conclusion
)
```

This is a **hardcoded phase/question schedule** that directly contradicts the architecture mandate that question flow should be dynamic and LLM-driven. The `total_questions` is fixed at 15, but adaptive interviews should not have fixed counts.

---

## Phase 7: Frontend Compatibility — ❌ FAIL (Critical)

### Frontend Calls the WRONG Backend API

**File:** `frontend/src/services/interviewService.ts`

The frontend service calls OLD routes from `app/api/interview.py`:

| Frontend Call | Old Route | New Route (Correct) |
|--------------|-----------|-------------------|
| `startSession` | `POST /companies/{id}/interview/session` | `POST /api/interviews` |
| `getSessionStatus` | `GET /companies/{id}/interview/session/{sid}` | `GET /api/interviews/{sid}/status` |
| `getNextQuestion` | `POST /companies/{id}/interview/session/{sid}/next` | `POST /api/interviews/{sid}/questions/next` |
| `submitAnswer` | `POST /companies/{id}/interview/answer` | `POST /api/interviews/{sid}/answers` |
| `getReport` | `POST /companies/{id}/interview/review` | `GET /api/interviews/{sid}/summary` |

**Severity:** CRITICAL — Every frontend API call targets the wrong backend.

### Frontend Types Don't Match Either API Response

**File:** `frontend/src/types/interview.ts`

The `InterviewSession` interface expects:
```typescript
{
  session_id: string;     // ✅ Both APIs return this
  company_id: number;     // ⚠️ Only old API includes this
  job_role: string;       // ✅ Both include
  status: string;         // ✅ Both include
  current_phase: string;  // ✅ Both include
  current_question_number: number;  // ✅ Both include
  total_questions: number; // ✅ Both include
  difficulty_level?: number; // ❌ Neither API returns this consistently
  interview_mode?: InterviewMode; // ❌ Neither API returns this
}
```

The `Question` interface expects a `question_id` field that **neither backend API returns**. The old API returns `question` string, the new API returns `question` with `question_number`.

The `AnswerEvaluation` interface expects `evaluation`, `score`, `phase`, `question_number`, `difficulty_level`, `interview_status` — the old API does return these fields but in a flat structure, while the new API wraps them differently.

### Frontend Has Two Code Paths: Controller vs Direct Service

**File:** `frontend/src/controllers/interviewController.ts`
**File:** `frontend/src/state/interviewStore.tsx`

The frontend has a controller layer that wraps `interviewService.ts` calls with state management. However, the state store (`interviewStore.tsx`) also manages question number and phase tracking, duplicating values that the architecture says should be backend-controlled.

### Old `app.js` Frontend

**File:** `frontend/app.js`
This plain JavaScript file is a completely separate frontend implementation that also talks to the old API. Having two frontend implementations (`frontend/app.js` and `frontend/src/`) is a maintenance burden.

---

## Summary Table

| Phase | Status | Critical Issues |
|-------|--------|----------------|
| 1. API Layer | **FAIL** | Duplicate routers (new + old), missing rag-status endpoint |
| 2. Orchestrator | **FAIL** | Only serves new API, old API bypasses entirely |
| 3. LangGraph | **FAIL** | Missing error paths, no conditional edges, evaluation table unused |
| 4. RAG Integration | **FAIL** | No fallback for missing company context, context not guaranteed in questions |
| 5. AI Generation | **FAIL** | Hardcoded fallback questions violate architecture rules |
| 6. Database | **FAIL** | `create_question` stores data in wrong columns, orphaned tables |
| 7. Frontend | **FAIL** | Frontend calls old API, types don't match either API response |

**Overall:** ❌ **BACKEND ARCHITECTURE IS BROKEN. DO NOT PROCEED WITH FRONTEND CHANGES UNTIL BACKEND IS UNIFIED.**

---

## Immediate Actions Required

1. **Delete one API router** — Choose LangGraph (`app/api/interview_agent.py`) as the target, remove `app/api/interview.py` and its `include_router()` from `main.py`
2. **Fix `create_question` bug** — Swap `message_type` and `content` in `app/repositories/message_repository.py`
3. **Create `EvaluationRepository`** — Implement `app/repositories/evaluation_repository.py` and update `answer_evaluator_node.py` to write to `interview_evaluations` table
4. **Remove hardcoded fallback questions** — Make `question_generation_node.py` always call LLM
5. **Add RAG fallback** — Handle missing company context gracefully in `company_context_node.py`
6. **Update frontend** — Rewrite `interviewService.ts` to call `/api/interviews/...` routes with correct request/response schemas
7. **Align frontend types** — Update `frontend/src/types/interview.ts` to match the actual LangGraph API response format
8. **Implement `/api/interviews/{session_id}/rag-status`** endpoint