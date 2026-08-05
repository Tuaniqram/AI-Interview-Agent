# AURA V5 — Architecture

AURA V5 turns the V4 evidence-driven interview into a *reasoning system*: a
durable **InterviewBrain** holds the interview's working state, company and
candidate **intelligence** are injected before the session starts, hypotheses
are updated **Bayesian-ly** with a live **evidence graph**, difficulty is
governed by a **6-dimension DifficultyProfile**, and everything is persisted to
**9 V5 tables**. All of it degrades gracefully offline — RAG and LLM failures
fall back to deterministic paths so a session can always start and continue.

## 1. Layers

```
┌────────────────────────────────────────────────────────────┐
│ API layer                                                   │
│   app/api/interview_ws.py   (WS protocol — v4/AURA)         │
│   app/api/interview_v4.py    (HTTP shim — backward compat)  │
│   app/api/v1/intelligence.py (POST /intelligence/build,     │
│                                GET /intelligence/brain/{id}) │
└───────────────┬────────────────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────────────────┐
│ Orchestration layer — app/engine/                          │
│   InterviewEngine: start_session / process_answer /        │
│   _process_v4_answer / _process_v5_answer / _finalize      │
│   _govern_difficulty / _persist_* (best-effort)            │
│   builders.py: start / answer / state / report responses   │
└───────────────┬────────────────────────────────────────────┘
                │  dict in / dict out (agent boundary)
┌───────────────▼────────────────────────────────────────────┐
│ Agent layer — app/agents/ (V4 signatures preserved)        │
│   session_init, company_context, candidate_profile,        │
│   competency_planner, strategy_brain, hypothesis_node,     │
│   question_generator (company_context aware),              │
│   unified_evaluator, evidence_extractor (evidence graph),  │
│   difficulty_governor (6-dim profile, conditional skip),   │
│   reflection_engine, synthesis, action_router              │
└───────────────┬────────────────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────────────────┐
│ State — app/core/                                          │
│   InterviewBrain (dataclass) + interview_state (transport) │
│   dict ⟷ brain; sync after every agent pass               │
└────────────────────────────────────────────────────────────┘

  Intelligence (pre-session)   Persistence (post-turn)
  app/intelligence/            app/models/db.py (9 V5 tables)
    build_interview_intelligence  alembic b7c9d1e2f3a4
  prompts/intelligence/*.md
```

## 2. InterviewBrain — the central reasoning state

`app/core/interview_brain.py` — a single dataclass is the authoritative state.
Every agent pass converts it to a V4-style flat dict and reconciles it back
(`sync_brain`), so existing agents and the `v4_session_store` work unchanged.

- `to_dict()` matches the V4 flat key structure exactly.
- `from_dict()` accepts V5 brain dicts *and* legacy V4 state dicts (unknown keys
  are preserved via `setattr`, since agents add ad-hoc fields).
- Holds V5 artifacts: `difficulty_profile`, `company_brain`,
  `interview_blueprint`, `candidate_brain`, `initial_hypotheses`,
  `evidence_requirements`, `candidate_assessment`, `evidence_graph`.

## 3. Engine — orchestration and run-mode routing

`app/engine/engine.py` — `InterviewEngine`:

- `start_session(state, build_intelligence=False, **intelligence)` runs the
  start node chain. When `build_intelligence=True` and no bundle is passed, it
  calls `build_interview_intelligence(...)` (best-effort) and sets the 6
  intelligence keys on the brain before the nodes run.
- `process_answer(session_id, answer)` sanitizes, evaluates, and extracts
  evidence, then **routes by `flow_type`**:

  | flow_type                | pipeline                                          |
  |--------------------------|---------------------------------------------------|
  | `v4_evidence_driven` (and any non-v5) | `_process_v4_answer`: plain `difficulty_governor(state)` mid-turn, V4 order |
  | `v5_evidence_driven`     | `_process_v5_answer`                              |
  | `v5_company_context`     | `_process_v5_answer` + company brain injected into question prompts |
  | `difficulty_probing`     | `_process_v5_answer` (difficulty-focused flow)    |

- `_process_v5_answer` places the **conditional-LLM difficulty governor right
  before question generation** (after hypothesis selection, so difficulty adapts
  to the target about to be asked). The governor uses
  `use_llm=not should_skip_llm_governor(state)` — the LLM runs for the first
  four turns, then only when the last read is not decisive.
- `_process_v4_answer` keeps the legacy placement and the plain
  `difficulty_governor(state)` call.
- Optional `v5_persister` seam: when provided (exposing
  `save_snapshot(brain)`), the V5 brain/evidence-graph/timeline snapshot is
  persisted after each V5 turn. No persister → no DB calls (the WS flow and
  tests are unaffected).

## 4. Agent upgrades

### Bayesian hypotheses — `app/agents/hypothesis_manager.py`
- Every hypothesis carries `probability` alongside `confidence`; both start at
  `PRIOR_CONFIDENCE = 0.5` (inverted communication hypothesis starts at `0.0`).
- `bayesian_update()` folds each evidence item into the posterior and **mirrors
  it back into `confidence`** so the legacy delta path and reporting stay
  consistent.
- Refutation mapping: `confidence <= REFUTE_THRESHOLD and status != "untested"`
  → `refuted`. The legacy `update_hypotheses()` delta path is preserved.

### Evidence graph — `app/agents/evidence_extractor_node.py`
- `_update_evidence_graph()` maintains `{nodes, edges}`:
  - nodes: per-competency score aggregates (`average_score`, count);
  - edges: `evidence_id -> hypothesis_id` tagged with `weight` (relevance) and
    `support` (score above/below midpoint vs. hypothesis direction).
- Surfaced in the final report via `build_report_response` (
  `evidence_graph.competency_nodes` / `.evidence_edges`) and in
  `InterviewBrain.evidence_graph`.

### Difficulty governor — `app/agents/difficulty_governor.py`
- `DifficultyProfile` has six dimensions: `problem_complexity`,
  `abstraction_depth`, `time_pressure`, `scaffolding_needed`,
  `precision_required`, `follow_up_aggression`.
- `build_difficulty_profile(state, delta, rationale)` emits both a structured
  `dimensions` list and flat numeric keys (e.g. `profile["abstraction_depth"]`).
- `should_skip_llm_governor(state)` decides when the deterministic path is
  enough; `_govern_deterministic` keeps its plain-function signature.

### Question generator — `app/agents/generation/question_generator.py`
- `_company_context(state)` summarizes the company brain (vision, stack,
  culture, success signals) and threads it into the merged
  `interview/question_generation.md` prompt (conductor persona + question
  generation in one file) as `{{company_context}}` (degrades to `N/A` when no
  company brain exists).

## 5. Intelligence module

`app/intelligence/__init__.py` — facade `build_interview_intelligence(*, job_role,
department_id, style, candidate_profile, candidate_id, resume_text,
required_competencies, scorecard_competencies, use_rag, use_llm)` returns
exactly 6 keys:

1. `company_brain`        — `company_intelligence_builder` (RAG → LLM → keyword fallback)
2. `interview_blueprint`  — `interview_blueprint_builder` (LLM → deterministic)
3. `candidate_brain`      — `resume_analyzer` + `candidate_intelligence_builder`
4. `initial_hypotheses`   — from resume/candidate profile (all carry `probability`)
5. `evidence_requirements`— `scorecard_resolver` (deterministic mapping)
6. `candidate_assessment` — `candidate_matcher` match score, gaps, probes, risks

Every stage is best-effort; RAG ingestion is **not** part of the module (use the
existing `store_department_knowledge` / `get_department_retriever(department_id)`).
Prompts live in `prompts/intelligence/` (`company_brain.md`,
`interview_blueprint.md`, `resume_analysis.md`), loaded through
`PromptLoader` (nested-path + caching support added).

## 6. Persistence

9 new tables in `app/models/db.py` (migration `b7c9d1e2f3a4`):

| table | purpose |
|-------|---------|
| `company_brains`              | V5 company intelligence bundle |
| `interview_blueprints`        | V5 interview plan (objectives, phases, hypothesis template) |
| `scorecards`                  | per-interview weighted competencies + required evidence level |
| `candidate_brains`            | V5 candidate intelligence |
| `candidate_documents`         | resumes / parsed artifacts |
| `candidate_evidence_requirements` | per-competency probes + evidence level |
| `interview_brain`             | central reasoning snapshot (hypotheses, evidence, scores, difficulty) |
| `evidence_graph`              | nodes + edges snapshot per session |
| `interview_timeline`          | event timeline (question, evaluation, hypothesis shift, decision) |

`POST /intelligence/build` best-effort persists into these; `GET
/intelligence/brain/{session_id}` reads the brain + graph + timeline back out.

## 7. Backward-compatibility contract

- Tests still import `_build_*_response`, `_extract_answer_turn`,
  `_persist_answer_turn`, `_persist_completion` from `app.api.interview_v4`
  (dict-based shim) and monkeypatch `app.api.interview_v4._store`.
- `build_start_response`/`build_state_response` re-exported through the engine
  builders; the WS layer adds the `type` envelope itself.
- `_govern_deterministic`, `_extract_answer_turn`, `_persist_*` keep their
  signatures. Agent node signatures are unchanged (dict in / dict out).
- `v3/` untouched; `app/agents/` retained; no LangGraph in new code; Pinecone
  still used for RAG.

## 8. Tests

- `tests/test_intelligence.py` (15) — document analysis, scorecard resolver,
  blueprint/resume, matcher, facade, engine injection.
- `tests/test_intelligence_api.py` (6) — bundle build, best-effort persistence,
  brain snapshot read.
- `tests/test_v5_agents.py` (14) — Bayesian updates, 6-dim difficulty profile,
  conditional LLM skip, evidence graph, report exposure.
- `tests/test_engine_v5_flow.py` (7) — run-mode routing, V5 persister seam,
  company-context question injection.
- Existing V4/WS/AURA suites remain green (`v4_evidence_driven` keeps the V4
  pipeline; the WS protocol test runs the `v5_evidence_driven` flow through
  `_process_v5_answer`).
