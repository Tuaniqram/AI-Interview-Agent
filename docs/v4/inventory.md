# v4 Engine Inventory

Reference inventory of the v4 evidence-driven interview engine: nodes, prompts, LLM budget, API surface, and known deviations from `architecture.md`.

> This document is generated/maintained by hand. Run `python -m pytest tests/ -q` and `test_prompt_integrity.py` to verify prompt wiring after any change.

---

## 1. Node Inventory

The v4 engine is a linear orchestration (no LangGraph compile) run by `app/api/interview_agent.py` (`_run_v4_start` / `_run_v4_answer`) and `app/api/interview_v4.py`. Both run the **identical node sequence**.

### 1.1 Start sequence (once per session)

| # | Node | File | LLM? | Prompt | Notes |
|---|------|------|------|--------|-------|
| 1 | `session_init_node` | `app/agents/session_init_node.py` | No | — | Seeds state, defaults |
| 2 | `department_context_node` | `app/agents/company_context_node.py` | No | — | RAG retrieval (Pinecone), no LLM |
| 3 | `candidate_profile_node` | `app/agents/candidate_profile_node.py` | No | — | Profile/DB load, deterministic |
| 4 | `competency_planner_node` | `app/agents/competency_planner_node.py` | No | — | Deterministic planner (replaces doc's `question_planner_node`) |
| 5 | `strategy_brain_node` | `app/agents/strategy_brain_node.py` | **Yes (1x)** | `prompts/interview/strategy_brain.md` | Runs once, cached in state |
| 6 | `hypothesis_node` | `app/agents/hypothesis_node.py` | No | — | Deterministic hypotheses; each carries a `competency` id via `map_skill_to_competency` (`SKILL_TO_COMPETENCY`) so the evidence extractor can match by competency |
| 7 | `question_generator_node` | `app/agents/question_generator_node.py` | **Yes (1/answer)** | `prompts/interview/question_generation.md` | LLM first; deterministic templates + `_fallback_question` on failure |

### 1.2 Answer loop (per answer)

| # | Node | File | LLM? | Prompt | Notes |
|---|------|------|------|--------|-------|
| 8 | `unified_evaluator_node` | `app/agents/unified_evaluator_node.py` | **Yes (1 or 6/answer)** | `prompts/evaluation/unified_evaluator.md` (unified) or `{dim}_evaluator.md` ×6 (parallel) | Mode from `interview_style.evaluator_mode` |
| 9 | `evidence_extractor_node` | `app/agents/evidence_extractor_node.py` | No | — | Deterministic, updates `competency_summary` |
| 10 | `reflection_engine` | `app/agents/reflection_engine.py` | No | — | Deterministic; outputs `reflection_action` |
| 11 | `synthesis_node` | `app/agents/synthesis_node.py` | **Yes (1x)** | `prompts/evaluation/synthesis.md` | Fallback `_fallback_synthesis` on failure |

### 1.3 Helpers

| Helper | File | Notes |
|--------|------|-------|
| `route`, `route_after_planner` | `app/agents/action_router.py` | Pure routing on `reflection_action` (`probe` / `change_competency` / `finish`) |

### 1.4 Flow

```
start:   session_init → company_context → candidate_profile → competency_planner
         → strategy_brain (LLM) → hypothesis → question_generator (LLM)

answer:  unified_evaluator (LLM) → evidence_extractor → reflection_engine
         ├─ change_competency → competency_planner → route_after_planner
         │       ├─ finish → synthesis (LLM)
         │       └─ else   → hypothesis → question_generator (LLM)
         └─ else (probe/continue) → hypothesis → question_generator (LLM)
```

---

## 2. Prompt Inventory

### 2.1 Used by the v4 engine (4 active + 6 parallel-only)

| Prompt | Used by | Mode |
|--------|---------|------|
| `prompts/interview/strategy_brain.md` | `strategy_brain_node` | always |
| `prompts/interview/question_generation.md` | `question_generator_node` | always (also legacy v3 path) |
| `prompts/evaluation/unified_evaluator.md` | `unified_evaluator_node` | `evaluator_mode=unified` |
| `prompts/evaluation/synthesis.md` | `synthesis_node` | always |
| `prompts/evaluation/{technical,communication,reasoning,behavioral,confidence,completeness}_evaluator.md` | `unified_evaluator_node._parallel_evaluator` | `evaluator_mode=parallel` only |

### 2.2 Legacy-only prompts (v3 engine, not used by v4)

| Prompt | Loaded by |
|--------|-----------|
| `prompts/system/interviewer_system.md` | `question_generation_node` |
| `prompts/system/followup_system.md` | `question_generation_node` |
| `prompts/system/evaluator_system.md` | `answer_evaluator_node` |
| `prompts/interview/adaptive_question.md` | `question_generation_node` |
| `prompts/interview/phase_decision.md` | `phase_decision_node` |
| `prompts/interview/interview_flow.md` | `interview_flow_node` |
| `prompts/interview/skill_tracker.md` | `skill_tracker_node` |
| `prompts/interview/inquisitor.md` | `inquisitor_node` |
| `prompts/evaluation/answer_evaluation.md` | `answer_evaluator_node` |
| `prompts/evaluation/scoring_rules.md` | `answer_evaluator_node` |

### 2.3 Dormant prompts (kept, no load site)

| Prompt | Note |
|--------|------|
| `prompts/interview/question_generator.md` | Replaced by `question_generation.md` |
| `prompts/interview/evidence_extractor.md` | Extractor is deterministic |
| `prompts/marketplace/job_description.md` | Marketplace domain (outside engine) |

### 2.4 Placeholder contract

`app/services/prompt_loader.py` substitutes only keys passed by the caller; **missing keys render as literal `{{key}}`**. Any node that loads a prompt must pass every placeholder that prompt file contains. Verified by `tests/test_prompt_integrity.py`.

---

## 3. LLM Call Budget (per 10-question session)

| Mode | strategy_brain | question_generator | evaluator | synthesis | Total |
|------|---------------|-------------------|-----------|-----------|-------|
| unified | 1 | 10 | 10 | 1 | **22** |
| parallel | 1 | 10 | 60 | 1 | **72** |

`evaluator_mode=parallel` is the only enterprise/research style (FAANG); everything else is unified.

---

## 4. API Surface Map

| Endpoint | Handler | Engine |
|----------|---------|--------|
| `POST /api/v1/interviews/{session_id}/questions/next` | `app/api/interview_agent.py:395` → `_run_v4_start:177` / `_run_v4_answer:217` | v4 |
| `POST /api/v1/interviews/{session_id}/answers` | `app/api/interview_agent.py:443` → `_run_v4_answer` | v4 |
| `GET /api/v1/interviews/{session_id}/summary` | `app/api/interview_agent.py:527` | v4 |
| `POST /api/v1/interviews/{session_id}/start` (practice) | `app/api/interview_agent.py:411` | v4 |
| `POST /api/v1/public/interviews/{token}/start` (listing) | `app/api/v1/public.py:16` → `app/marketplace/service.py:199` `start_public_interview` | v4 |
| `POST /interviews/v4/*` | `app/api/interview_v4.py` | v4 (standalone demo only — `frontend/interview-v4.html`) |
| Legacy v3 routes | `app/api/interview_agent.py` (engine `!= v4`) | v3 |

**Listing vs practice start**: both seed the identical v4 node sequence and LLM budget. Differences are setup-only:

| Aspect | Practice start | Public (listing) start |
|--------|---------------|------------------------|
| Session type | `mock` | `public` |
| Competencies | default taxonomy | org scorecard/template → `resolve_competencies` |
| RAG context | — | department Pinecone retrieval |
| Interview style | from request | from listing |

---

## 5. Deviations from `docs/v4/architecture.md`

The architecture doc describes three additional LLM-backed components that are **not implemented**; the engine intentionally uses deterministic equivalents (keep them that way):

| Doc component | File in doc | Implemented as |
|---------------|-------------|----------------|
| `question_planner_node` (LLM) | `app/agents/question_planner_node.py` + `prompts/interview/question_planner.md` | `competency_planner_node` (deterministic) |
| `consistency_checker_node` (LLM) | `app/agents/consistency_checker_node.py` + `prompts/interview/consistency_checker.md` | none (not needed for the linear engine) |
| `observation_analyzer` | `app/agents/observation_analyzer.py` | observations handled inline in `unified_evaluator_node` |
| `reflection_engine.md` prompt | `prompts/interview/reflection_engine.md` | `reflection_engine.py` is deterministic, no prompt |

Related doc-file deltas that are intentional:
- `question_generator.md` (doc §3.3 file name) → implemented as `question_generator_node.py` using **`question_generation.md`**.
- Synthesis prompt lives in `prompts/evaluation/synthesis.md` (externalized from `synthesis_node.py` inline f-string).
- Parallel evaluator prompts (`{dim}_evaluator.md`) were missing → created; the parallel mode previously crashed with `FileNotFoundError` at `unified_evaluator_node.py:160`, producing `null` scores.

---

## 6. Testing Surface

| Test file | Covers |
|-----------|--------|
| `tests/test_prompt_integrity.py` | Every prompt file exists for every load site; every placeholder rendered |
| `tests/test_deterministic_nodes.py` | planner, hypothesis, evidence_extractor, reflection_engine, action_router, fallback question |
| `tests/test_llm_nodes.py` | question_generator (LLM + fallback), unified evaluator (unified + parallel), synthesis — with mocked `get_llm_service` |
| `tests/test_api_v4.py` | v4 API wiring (mock engine) |
| `tests/test_marketplace_start.py` | `start_public_interview` seeds a v4 session |
