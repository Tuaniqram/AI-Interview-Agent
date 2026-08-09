# AURA Engine — Architecture Documentation (V5)

> **Companion guide:** `docs/FULL_SYSTEM.md` is the system-wide reference — it
> covers the marketplace/listing flow, scorecards, the interview lifecycle
> (start → finish), the complete REST + WebSocket API surface, and the V5
> `InterviewEngine` orchestration layer. This document is the deep-dive on the
> engine internals (nodes, prompts, agent packages, state).

## Table of Contents

1. [System Overview](#system-overview)
2. [Core File & Folder Tree](#core-file--folder-tree)
3. [Frontend Reference](#frontend-reference)
4. [Interview Entry Points](#interview-entry-points)
5. [V5 AURA Engine — Interview Lifecycle](#v5-aura-engine--interview-lifecycle)
6. [Agent Node Reference (agents/)](#agent-node-reference-agents)
7. [Engine State](#engine-state)
8. [Prompt Templates (prompts/)](#prompt-templates-prompts)
9. [WebSocket Protocol](#websocket-protocol)
10. [Data Flow Diagrams](#data-flow-diagrams)
11. [Persistence & Write-Back](#persistence--write-back)
12. [Event Log (Tier 3 Observability)](#event-log-tier-3-observability)
13. [Session Store Backends](#session-store-backends)
14. [LLM Tiering & Cost Control](#llm-tiering--cost-control)

---

## System Overview

AURA (Adaptive Unified Reasoning Agent) is the **only** interview engine in use.
It is a hypothesis-driven, evidence-driven interview engine that:

- Generates **hypotheses** about a candidate and tests them through targeted questions
- Tracks **evidence** per competency across the interview
- Adapts **difficulty** in real-time based on performance
- Supports the **conductor persona** — acknowledgement → bridge → question turns
- Produces a **hiring recommendation** with verdict, confidence, and coverage
- Runs a deterministic **director** + **decision-review** stage so the interview's
  direction and the final verdict are explainable, not just LLM outputs

The engine is **imperative** (no LangGraph). Sessions are driven over a
WebSocket protocol; a thin REST layer only starts sessions and serves the report.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CANDIDATE EXPERIENCE                         │
│                                                                     │
│  Practice / Marketplace / Public link → WS Interview → Report       │
└──────────────┬───────────────────────────────┬─────────────────────┘
               │                               │
    ┌──────────▼──────────┐        ┌───────────▼──────────────────┐
    │   REST (session)    │        │   WebSocket (conversation)   │
    │  candidates/service │        │   app/api/interview_ws.py    │
    │  marketplace/service│        │   → InterviewEngine          │
    └──────────┬──────────┘        └───────────┬──────────────────┘
               │                               │
    ┌──────────▼───────────────────────────────▼──────────────────┐
    │                   V4 SESSION STORE                          │
    │  MemoryV4SessionStore  (default, in-memory + Postgres)     │
    │  RedisV4SessionStore   (Redis hot tier + Postgres CP)      │
    │         app/services/v4_session_store.py                    │
    │         SESSION_STORE_BACKEND=memory | redis                │
    └──────────┬───────────────────────────────┬──────────────────┘
               │                               │
    ┌──────────▼───────────────────────────────▼──────────────────┐
    │                 V5 ENGINE (split modules)                   │
    │  lifecycle.start_session → answer_processor.process_answer  │
    │  routing.route_answer → decision.finalize_session           │
    │  persistence.* best-effort DB writes; builders.* responses  │
    │                                                             │
    │  Start:  session_init → department_context → candidate_     │
    │          profile → competency_planner → strategy_brain →    │
    │          hypothesis → question_generator                    │
    │                                                             │
    │  Answer: unified_evaluator → evidence_extractor →           │
    │          explainable_scoring → reflection_engine → director │
    │          → difficulty_governor → hypothesis_node →          │
    │          question_generator                                 │
    │                                                             │
    │  Finish: synthesis → hiring_decision → decision_review      │
    │                                                             │
    │  Observability: EventLog.append() at each pipeline stage    │
    └─────────────────────────────────────────────────────────────┘
```

---

## Core File & Folder Tree

```
app/
├── main.py                          # FastAPI app; mounts all routers (engine = WS only)
├── api/
│   ├── interview_ws.py              # WS /ws/interview/{session_id} — THE conversation engine
│   │                                #   start/resume: _start_v4_engine()      (line 128)
│   │                                #   handler: interview_websocket()         (line 180)
│   │                                #   cleanup: start_cleanup_task()          (line 66)
│   ├── interview_agent.py           # REST summary ONLY (post-interview):
│   │                                #   GET /interviews/{id}/summary  (line 166)
│   │                                #   reads DB repos + V5 interview_brain snapshot
│   │                                #   (interview_v4.py was deleted — Phase 10)
│   └── v1/
│       ├── candidates.py            # POST /api/v1/candidates/practice/start
│       ├── marketplace.py           # POST /api/v1/marketplace/interviews/{id}/start
│       └── public.py                # POST /api/v1/public/interviews/{token}/start
│
├── engine/                          # V5 orchestration (Phase 1 split) — thin coordinator
│   ├── engine.py                    # InterviewEngine — start/process/get_state/get_brain
│   ├── lifecycle.py                 # start_session: intelligence + start node chain
│   ├── answer_processor.py          # process_answer: sanitize → evaluate → evidence → score
│   ├── routing.py                   # route_answer: reflection → director → governor → emit
│   ├── decision.py                  # finalize_session: synthesis → decision → review → report
│   ├── persistence.py               # best-effort DB writes (evidence/turn/completion/snapshot)
│   └── builders.py                  # build_start/answer/state/report_response
│
├── agents/                          # Pipeline nodes grouped into capability packages
│   ├── init/                        # session/context/profile initialization
│   │   ├── session_init.py          # sync: initialize state
│   │   ├── company_context.py       # RAG (Pinecone) department context
│   │   └── candidate_profile.py     # DB profile load
│   ├── planning/
│   │   ├── strategy_planner.py      # LLM interview strategy
│   │   ├── competency_planner.py    # pure competency planning + node wrapper
│   │   ├── difficulty_engine.py     # adaptive difficulty (LLM + fallback)
│   │   └── action_router.py         # route_after_planner() only
│   ├── reasoning/
│   │   ├── hypothesis_engine.py     # Bayesian belief + hypothesis node
│   │   ├── information_gain.py      # entropy-based target selection (EIG)
│   │   ├── evidence_engine.py       # evidence + quality annotation + evidence graph
│   │   ├── contradiction_engine.py  # contradictions / sufficiency / hiring rec / action
│   │   └── reflection_engine.py     # node wrapper over the contradiction capability
│   ├── generation/
│   │   └── question_generator.py    # LLM question gen + conductor turn
│   ├── evaluation/
│   │   ├── candidate_evaluator.py   # LLM 6-dimension unified evaluation
│   │   ├── scoring.py               # explainable_scoring_node (deterministic composite)
│   │   └── synthesis.py             # LLM final report
│   └── decision/
│       ├── director.py              # director_controller — pure next-action decision
│       ├── hiring_decision.py       # LLM hiring decision + deterministic fallback
│       └── decision_review.py       # decision_review_node — Evidence → Draft → Review → Final
│
├── core/
│   ├── interview_state.py           # InterviewState TypedDict + brain<->dict transport
│   └── interview_brain.py           # InterviewBrain wrapper (.to_dict, .bump_version, …)
│
├── services/
│   ├── v4_session_store.py          # dual-backend session store (memory | Redis)
│   │                                #   MemoryV4SessionStore — in-memory + Postgres write-behind
│   │                                #   RedisV4SessionStore  — Redis hot tier + Postgres checkpoint
│   │                                #   SESSION_STORE_BACKEND env selects backend (default: memory)
│   ├── v5_brain_persister.py        # V5BrainPersister — brain → DB snapshot rows (opt-in)
│   ├── event_log.py                 # best-effort append-only event log (interview_events table)
│   │                                #   get_event_log().append(session_id, event_type, payload)
│   ├── cache.py                     # Redis cache (async, TTL-based, separate from session store)
│   ├── repositories.py              # get_session_repo() / get_message_repo() / get_evaluation_repo()
│   ├── llm_service.py               # OpenAI-compatible LLM invocation (tier-aware)
│   └── prompt_loader.py             # template prompt loading + caching
│
├── models/
│   └── llm.py                       # tier registry: get_llm("cheap"|"strong"|"openrouter")
│
├── candidates/service.py            # start_practice() — seeds V4 state (line 274)
├── marketplace/service.py           # start_public_interview() — seeds V4 state (line 199)
├── repositories/                    # session / message / evaluation / evidence repos
│
prompts/
├── interview/
│   ├── strategy_brain.md            # strategy_planner
│   └── question_generation.md       # question_generator (merged conductor persona)
├── evaluation/
│   ├── unified_evaluator.md         # unified_evaluator_node (unified mode)
│   └── synthesis.md                 # synthesis_node
├── difficulty_governor/
│   └── difficulty_governor.md       # difficulty_governor
├── decision/
│   └── hiring_decision.md           # hiring_decision_node
├── intelligence/
│   └── …                            # company intelligence / resume analysis prompts
└── marketplace/
    └── job_description.md           # listing description generation

frontend/src/
├── services/
│   ├── candidateService.ts          # POST /api/v1/candidates/practice/start (line 68)
│   ├── marketplaceService.ts        # POST /api/v1/marketplace/interviews/{id}/start (line 29)
│   ├── interviewWebSocket.ts        # WS client — /ws/interview/{session_id}?token= (line 46)
│   ├── interviewController.ts       # session orchestration (connect, submitAnswer, …)
│   └── interviewService.ts          # GET /interviews/{session_id}/summary (only live method)
├── state/
│   └── interviewStore.tsx           # React store — wires controller + WS events
│                                    #   (imports controller:16, WS:17; WS handlers:365,371)
├── routes/
│   └── InterviewReport.tsx          # GET /interviews/{id}/summary (line 47)
└── pages/
    ├── candidate/                   # CandidateInterviewDetail, Dashboard, Interviews
    ├── opportunity-hub/             # OppHubInterviewDetail (marketplace listing start)
    └── public-interview/
        └── PublicInterview.tsx      # token-link start (line 18)
```

---

## Frontend Reference

The frontend talks to the engine in exactly three places:

| Concern | Frontend file | Backend |
|---|---|---|
| Start practice interview | `candidateService.ts:68` → `POST /api/v1/candidates/practice/start` | `app/candidates/service.py:274` `start_practice()` → seeds V4 store |
| Start marketplace listing | `marketplaceService.ts:29` → `POST /api/v1/marketplace/interviews/{id}/start` | `app/marketplace/service.py:199` `start_public_interview()` → seeds V4 store |
| Start public token link | `PublicInterview.tsx:18` → `POST /api/v1/public/interviews/{token}/start` | `app/api/v1/public.py:36` → same `start_public_interview()` |
| Drive the interview | `interviewWebSocket.ts:46` → `WS /ws/interview/{session_id}?token={token}` | `app/api/interview_ws.py:188` |
| Orchestrate + state | `interviewController.ts` + `interviewStore.tsx` (imports at :16-17, WS events at :365/:371) | — |
| View report | `InterviewReport.tsx:47` → `GET /interviews/{id}/summary` | `app/api/interview_agent.py:167` |

Routes: `/candidate/interviews/:interviewId` → `CandidateInterviewDetail`,
`/opportunity-hub/interviews/:interviewId` → `OppHubInterviewDetail`
(`frontend/src/routes/index.tsx:81,89`).

---

## Interview Entry Points

All three entry points land in the same V4 engine (`engine_version="v4"`,
AURA style):

```
POST /api/v1/candidates/practice/start        → start_practice()
POST /api/v1/marketplace/interviews/{id}/start → start_public_interview()
POST /api/v1/public/interviews/{token}/start  → start_public_interview()

WHAT HAPPENS (both services):
  1. Load template/listing, resolve scorecard or department competencies
  2. Create InterviewSession row (engine_version="v4")
  3. Seed V4 state in-memory:
     store.set(session_id, {session_id, job_role, department_id,
       interview_style: AURA style, competency_taxonomy, required_competencies,
       hypotheses: [], evidence_store: [], …})
  4. Return {session_id, token}

NO QUESTION IS ASKED YET — the first question comes over the WebSocket.
```

---

## V5 AURA Engine — Interview Lifecycle

### Phase 1: WebSocket Connect + First Question

```
WS /ws/interview/{session_id}?token={token}
File: app/api/interview_ws.py:189  →  _start_v4_engine() (line 128)
                                       → InterviewEngine.start_session(state, …)
                                         (app/engine/lifecycle.py)

CLIENT SENDS:
  {type: "start_interview", session_id: "uuid"}

SERVER:
  1. Reuse existing in-memory state if present (resume — idempotent)
  2. Load DB session row (job_role, department_id) — source of truth
  3. get_style("AURA"), resolve competencies (scorecard → department → default)
  4. Reconcile the seeded state into an InterviewBrain, run 7 sequential nodes:

  ┌─────────────────────────────────────────────────────────────┐
  │ NODE 1: session_init_node            (sync, no LLM)         │
  │   app/agents/init/session_init.py                           │
  │   Input: raw state → history, phase, question_number=0      │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ NODE 2: department_context_node      (Pinecone RAG)         │
  │   app/agents/init/company_context.py                        │
  │   Input: department_id, job_role, phase, weak skills        │
  │   Output: department_context[], department_requirements     │
  │   Phase-aware queries; cache 10min TTL, 200 max             │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ NODE 3: candidate_profile_node        (DB read)             │
  │   app/agents/init/candidate_profile.py                      │
  │   Output: candidate_profile {strengths, weaknesses, …}      │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ NODE 4: competency_planner_node       (sync, no LLM)        │
  │   app/agents/planning/competency_planner.py                 │
  │   Output: competency_plan[], next_competency, gaps          │
  │   Sort: priority → gap DESC → evidence_count ASC            │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ NODE 5: strategy_brain_node           (LLM temp=0.3)        │
  │   Prompt: prompts/interview/strategy_brain.md               │
  │   Output: interview_strategy{}, persona                     │
  │   Cached via strategy_cache_valid flag                      │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ NODE 6: hypothesis_node               (sync, no LLM)        │
  │   app/agents/reasoning/hypothesis_engine.py                 │
  │   Output: hypotheses[] (max 6), hypothesis_target           │
  │   Target: max expected information gain (entropy-based);    │
  │           deep_probe fallback when everything is settled    │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ NODE 7: question_generator_node       (LLM temp=0.8)        │
  │   Prompt: prompts/interview/question_generation.md          │
  │           (conductor persona merged)                        │
  │   Output: current_question, question_objective,             │
  │           conversation_turn {acknowledgement, bridge,       │
  │                              question} if conductor         │
  │   Fallback: deterministic templates per competency          │
  └─────────────────────────────────────────────────────────────┘

  5. EventLog: question_selected (target, selection_reason, information_gain)
  6. store.set(session_id, state)
  7. EventLog: session_started event (style, competencies, taxonomy)
  8. Return _build_start_response()

WS RESPONSE:
  {type: "question", session_id, status, job_role,
   conversation_turn: "acknowledgement\n\nbridge\n\nquestion",
   question: {text, number, target_competency, target_hypothesis},
   hypothesis_target, persona, difficulty, competencies}
```

### Phase 2: Candidate Submits Answer (Repeat Loop)

```
CLIENT SENDS:
  {type: "submit_answer", candidate_answer: "..."}

SERVER processes via process_answer() — app/engine/answer_processor.py:17

  PRE-PROCESSING
    1. sanitize_user_input() + detect_prompt_injection()
    2. EventLog: answer_received event (length, injection_signals)
    3. Guard: question_number >= max_questions → finalize_session
    4. Append {assistant: question} + {user: answer} to conversation_history

  EVALUATION PIPELINE — 4 sequential nodes

  ┌─────────────────────────────────────────────────────────────┐
  │ NODE A: unified_evaluator_node       (LLM temp=0.3, cheap)  │
  │   Prompt: prompts/evaluation/unified_evaluator.md           │
  │   Output: unified_evaluation{} — 6 dimensions scored:       │
  │     technical, communication, reasoning, behavioral,        │
  │     confidence, completeness — each with score, evidence,   │
  │     confidence, strengths, weaknesses                       │
  │   Modes: unified only (parallel mode removed)               │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ NODE B: evidence_extractor_node       (sync, no LLM)        │
  │   app/agents/reasoning/evidence_engine.py                   │
  │   Output: extracted_evidence[], evidence_store[],           │
  │           competency_summary{} (now annotated with quality: │
  │           strength/impact/ownership/complexity/contradiction│
  │           signals per evidence record), hypotheses          │
  │   DB persist: persist_evidence() — app/engine/persistence.py│
  │   EventLog: evidence_added                                  │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ NODE C: explainable_scoring_node       (sync, no LLM)       │
  │   app/agents/evaluation/scoring.py                          │
  │   Output: evaluation_score (weighted, renormalized over     │
  │           scored dims) + score_contributions[] +            │
  │           score_reasons[] (per-dim rationale, low-confidence│
  │           notes, strongest evidence, contradictions)        │
  │   Replaces the raw LLM composite with a deterministic value │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ NODE D: reflection_engine            (sync, rule-based)     │
  │   app/agents/reasoning/reflection_engine.py                 │
  │   Output: contradictions[], evidence_sufficiency{},          │
  │           hiring_recommendation{}, reflection_action,       │
  │           reflection_inputs{} (coverage_ratio,              │
  │           average_evidence_confidence, difficulty_reached,  │
  │           unanswered_hypotheses, budget_remaining,          │
  │           contradiction_count)                              │
  │   Contradiction: |latest − prev| ≥ 4.0                      │
  │   Sufficiency: tempered by evidence quality (min 0.5 floor) │
  │   Hard cap: 14 questions                                    │
  │   EventLog: action_decided                                  │
  └──────────────────────┬──────────────────────────────────────┘
  ┌──────────────────────▼──────────────────────────────────────┐
  │ DIRECTOR — app/agents/decision/director.py (sync, pure)     │
  │   Decides the next action from reflection signals + loop    │
  │   counters: CONTINUE | PROBE | CHANGE_COMPETENCY | FINISH   │
  │   Guards: 3 consecutive probes → rotate; belief ≥ 0.7 →     │
  │   probe for counter-evidence; budget exhausted → FINISH     │
  │   EventLog: director_decided                                │
  └──────────────────────┬──────────────────────────────────────┘
                         │
  ROUTING (app/engine/routing.py — route_answer, unified for all flow types):

    "FINISH"             → finalize_session (short-circuit)
    "CHANGE_COMPETENCY"  → competency_planner_node
                            └─ route_after_planner():
                                 target exists → hypothesis → governor → question
                                 no target     → finalize_session (finish)
    "PROBE"/"CONTINUE"   → hypothesis_node (runs exactly once on new evidence)

  NON-FINISH PATH:
    state = hypothesis_node(state)
    EventLog: question_selected (target, selection_reason, information_gain)
    EventLog: hypothesis_updated (before/after snapshots, only when changed)
    state = difficulty_governor(state)   # LLM for first 4 turns, then conditional
    EventLog: difficulty_changed
    state = question_generator_node(state)
    EventLog: question_asked event
    persist_answer_turn(session_id, brain)   # DB: question+answer+evaluation
    store.set(session_id, brain.to_dict())
    store.checkpoint(session_id, brain.to_dict())
    persist_v5_snapshot(session_id, brain, v5_persister)  # opt-in brain snapshots
    return build_answer_response()

WS RESPONSE:
  {type: "status", phase: "evaluating"}            (before processing)
  {type: "status", phase: "question_ready"}        (after processing)
  {type: "evaluation", session_id, evaluation: {scores, composite},
   next_question: {text, number, target_competency},
   evidence: {total, competency_progress}, hypothesis_progress, …}
```

### Phase 3: Interview Completion

```
When reflection/director signals FINISH:

  finalize_session() — app/engine/decision.py:21
    1. synthesis_node(state)          → final_report{}
       Prompt: prompts/evaluation/synthesis.md (LLM temp=0.3, strong tier)
    2. hiring_decision_node(state)    → hiring_decision{}
       Prompt: prompts/decision/hiring_decision.md (strong tier)
    3. decision_review_node(state)    → Evidence → Draft → Self Review → Final
       (app/agents/decision/decision_review.py): demotes hire/no_hire →
       undecided when evidence is insufficient / a competency is missing /
       confidence is overconfident / contradictions are serious; writes
       flag_review + demoted_to_undecided + review{} onto the brain
    4. persist_answer_turn()          → DB (messages + evaluations)
    5. persist_completion()           → DB (session completed, final score)
    6. store.set(session_id, state) + checkpoint
    7. EventLog: interview_finished event (final_score, hiring_recommendation)
    8. Return build_report_response()

WS RESPONSE:
  {type: "report", status: "completed",
   hiring_recommendation: {verdict, confidence, composite_score, coverage_ratio},
   competency_summary: {comp: {average_score, evidence_count, gap}},
   evidence_collected: N, questions_asked: N,
   hypothesis_outcomes: {confirmed, refuted, untested}}
```

---

## Agent Node Reference (agents/)

### Context & Profiling

| Node | File | Type | LLM | Input → Output |
|------|------|------|-----|----------------|
| `session_init_node` | `app/agents/init/session_init.py` | Sync | No | raw state → initialized state |
| `department_context_node` | `app/agents/init/company_context.py` | Async | No (Pinecone) | department_id → department_context[], requirements |
| `candidate_profile_node` | `app/agents/init/candidate_profile.py` | Async | No (DB) | candidate_id → candidate_profile{} |

### Planning

| Node | File | Type | LLM | Input → Output |
|------|------|------|-----|----------------|
| `competency_planner_node` | `app/agents/planning/competency_planner.py` | Sync | No | taxonomy + summary → competency_plan[], next_competency, gaps |
| `strategy_brain_node` | `app/agents/planning/strategy_planner.py` | Async | Yes (temp=0.3) | job_role + profile + style → interview_strategy{}, persona |
| `hypothesis_node` | `app/agents/reasoning/hypothesis_engine.py` | Sync | No | profile + taxonomy → hypotheses[], hypothesis_target |

### Question Generation

| Node | File | Type | LLM | Input → Output |
|------|------|------|-----|----------------|
| `question_generator_node` | `app/agents/generation/question_generator.py` | Async | Yes (temp=0.8) | hypothesis + competency + persona → current_question, question_objective, conversation_turn |

### Evaluation

| Node | File | Type | LLM | Input → Output |
|------|------|------|-----|----------------|
| `unified_evaluator_node` | `app/agents/evaluation/candidate_evaluator.py` | Async | Yes (temp=0.3, cheap tier) | question + answer → unified_evaluation{}, evaluation_score |
| `explainable_scoring_node` | `app/agents/evaluation/scoring.py` | Sync | No | unified_evaluation{} → evaluation_score, score_contributions[], score_reasons[] |
| `evidence_extractor_node` | `app/agents/reasoning/evidence_engine.py` | Sync | No | evaluation → extracted_evidence[] (quality-annotated), competency_summary, hypotheses |

### Decision & Adaptation

| Node | File | Type | LLM | Input → Output |
|------|------|------|-----|----------------|
| `difficulty_governor` | `app/agents/planning/difficulty_engine.py` | Async | Yes (temp=0.2, cheap tier, fallback) | evaluation + hypothesis → difficulty_level, delta, rationale |
| `reflection_engine` | `app/agents/reasoning/reflection_engine.py` | Sync | No | competency_summary + hypotheses → reflection_action, reflection_inputs{}, hiring_recommendation |
| `director_controller` | `app/agents/decision/director.py` | Sync | No | reflection signals + loop counters → action (CONTINUE/PROBE/CHANGE_COMPETENCY/FINISH) |
| `action_router` | `app/agents/planning/action_router.py` | Sync | No | `route_after_planner()` — post-planner finish check |

### Synthesis

| Node | File | Type | LLM | Input → Output |
|------|------|------|-----|----------------|
| `synthesis_node` | `app/agents/evaluation/synthesis.py` | Async | Yes (temp=0.3, strong tier) | full history + scores → final_report{} |

### Hiring Decision

| Node | File | Type | LLM | Input → Output |
|------|------|------|-----|----------------|
| `hiring_decision_node` | `app/agents/decision/hiring_decision.py` | Async | Yes (strong tier, fallback) | final_report + sufficiency → hiring_decision{} |
| `decision_review_node` | `app/agents/decision/decision_review.py` | Sync | No | hiring_decision{} + evidence → reviewed decision (demote/flag/cap confidence) |

---

## Engine State

### `app/core/interview_state.py`

The shared `InterviewState` TypedDict covering:

```
InterviewState:
  ├── Session: session_id, department_id, job_role, flow_type
  ├── Conversation: conversation_history[], current_phase
  ├── Questions: question_number, current_question, difficulty_level, questions_asked[]
  ├── Evaluation: candidate_answer, unified_evaluation{}, evaluator_mode,
  │               evaluation_score, extracted_evidence[],
  │               score_contributions[], score_reasons[]
  ├── Evidence: evidence_store[], competency_summary{}
  ├── Competency: competency_taxonomy[], required_competencies[], competency_plan[],
  │               next_competency, domain_label, company_competency_requirements[]
  ├── Strategy: interview_style{}, interview_strategy{}, persona, strategy_cache_valid
  ├── Hypotheses: hypotheses[], hypothesis_target, question_objective{}
  ├── Director: director{}, consecutive_probes, last_hypothesis_target_id
  ├── Reflection: reflection_action, reflection_inputs{}, evidence_sufficiency{},
  │               hiring_recommendation{}, contradictions[], consistency_checks[],
  │               observations[]
  └── Timing: start_time, nodes_executed[], skip_evaluation
```

### `app/services/v4_session_store.py`

Dual-backend store (`session_id → InterviewState`):

- **`MemoryV4SessionStore`** (default) — in-process dict with write-behind to Postgres `v4_session_state` table. Eviction at startup; `flush()` at shutdown.
- **`RedisV4SessionStore`** — Redis key `aura:sess:{id}` (TTL 24h) as hot shared tier, with Postgres as durable checkpoint. Lazy hydrates sessions from Postgres on `get`-miss so resume works across replicas. Degrades to in-process dict if Redis is unavailable.

Backend selected via `SESSION_STORE_BACKEND` env (`memory` | `redis`). Both expose
`get / get_or_raise / set / pop / flush / checkpoint / list_active / count`.

`checkpoint()` writes through to Postgres immediately (upserts `v4_session_state`,
bumps `state_version`), closing the crash-loss gap that existed when `flush()` ran
only at shutdown.

---

## Prompt Templates (prompts/)

### Interview Prompts

| File | Used By | Purpose |
|------|---------|---------|
| `prompts/interview/question_generation.md` | question_generator_node | First question + conductor persona (merged) |
| `prompts/interview/strategy_brain.md` | strategy_brain_node | Interview strategy planning |

### Evaluation Prompts

| File | Used By | Purpose |
|------|---------|---------|
| `prompts/evaluation/unified_evaluator.md` | unified_evaluator_node | All 6 dimensions in one call |
| `prompts/evaluation/synthesis.md` | synthesis_node | Final holistic report generation |

### Difficulty & Decision Prompts

| File | Used By | Purpose |
|------|---------|---------|
| `prompts/difficulty_governor/difficulty_governor.md` | difficulty_governor | Adaptive difficulty rationale (LLM path) |
| `prompts/decision/hiring_decision.md` | hiring_decision_node | Explicit hiring decision with rationale |

### Marketplace Prompts

| File | Used By | Purpose |
|------|---------|---------|
| `prompts/marketplace/job_description.md` | `marketplace_generator.py` | AI-generated listing descriptions |

---

## WebSocket Protocol

```
Endpoint: WS /ws/interview/{session_id}?token={token}
File: app/api/interview_ws.py:189

Connection flow:
  1. Server resolves candidate from ?token= (optional auth)
  2. Server accepts, sends: {type: "connected", session_id}

Client → Server messages:
  ┌────────────────────┬────────────────────────────────────────────┐
  │ type               │ payload                                    │
  ├────────────────────┼────────────────────────────────────────────┤
  │ ping               │ {}                                         │
  │ start_interview    │ {session_id}                               │
  │ submit_answer      │ {candidate_answer: "..."}                  │
  │ get_status         │ {}                                         │
  └────────────────────┴────────────────────────────────────────────┘

Server → Client messages:
  ┌────────────────────┬────────────────────────────────────────────┐
  │ type               │ payload                                    │
  ├────────────────────┼────────────────────────────────────────────┤
  │ connected          │ {session_id}                               │
  │ pong               │ {timestamp}                                │
  │ question           │ {session_id, status, question,             │
  │                     │  conversation_turn, hypothesis_target, …} │
  │ status             │ {phase: "evaluating" | "question_ready"}   │
  │ evaluation         │ {session_id, evaluation, next_question,    │
  │                     │  evidence, hypothesis_progress, …}        │
  │ report             │ {status: "completed",                      │
  │                     │  hiring_recommendation,                   │
  │                     │  competency_summary, …}                   │
  │ status_snapshot    │ {question_number, current_question, …}     │
  │ error              │ {detail: "..."}                            │
  └────────────────────┴────────────────────────────────────────────┘

Stale-connection cleanup: start_cleanup_task() (interview_ws.py:66)
```

Frontend client: `frontend/src/services/interviewWebSocket.ts` (builds the URL
at line 46-48, exposes `connect`, `startSession`, `submitAnswer`, `getStatus`,
event subscription). Consumed by `interviewStore.tsx` (imports at :17, WS event
handlers at :365/:371) via `interviewController.ts`.

---

## Data Flow Diagrams

### Complete Interview Turn

```
Candidate answers question (WS submit_answer)
        │
        ▼
┌─────────────────────┐
│ sanitize + injection│
│ detection + guard   │
│ EventLog:           │
│  answer_received    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐    LLM (temp=0.3, cheap tier)
│ unified_evaluator   │◄── unified_evaluator.md (single call)
│ 6 dimensions scored │
└────────┬────────────┘
         │ unified_evaluation{}
         ▼
┌─────────────────────┐
│ evidence_extractor  │
│ - extract evidence  │
│ - annotate quality  │
│   (strength, impact,│
│    ownership,       │
│    complexity,      │
│    contradiction)   │
│ - update competency │
│   summary           │
│ persist_evidence    │
│ EventLog:           │
│  evidence_added     │
└────────┬────────────┘
         │ evidence_store[], competency_summary{}, hypotheses[]
         ▼
┌─────────────────────┐
│ explainable_scoring │
│ deterministic       │
│ composite + reasons │
└────────┬────────────┘
         │ evaluation_score, score_contributions, score_reasons
         ▼
┌─────────────────────┐
│ reflection_engine   │
│ - contradictions    │
│ - sufficiency check │
│ - hiring rec        │
│ - reflection_inputs │
│ EventLog:           │
│  action_decided     │
└────────┬────────────┘
         │ reflection_action + inputs
         ▼
┌─────────────────────┐
│ director_controller │
│ (pure, deterministic│
│  action decision)   │
│ EventLog:           │
│  director_decided   │
└────────┬────────────┘
         │ action
         ▼
┌─────────────────────┐
│ routing (app/engine │
│ /routing.py)        │
│ CONTINUE/PROBE → hy-│
│  pothesis_node      │
│ CHANGE_COMP → plan- │
│  ner + route_after  │
│  _planner           │
│ FINISH → finalize   │
└────────┬────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 [Next Q]  [Finish]
    │         │
    │    ┌────▼─────────────┐
    │    │ synthesis_node   │
    │    │ final_report{}   │
    │    └────┬─────────────┘
    │         │
    │    ┌────▼─────────────┐
    │    │ hiring_decision  │
    │    │ _node → decision │
    │    │ _review_node     │
    │    └────┬─────────────┘
    │         │
    │    ┌────▼─────────────┐
    │    │ persist_answer_  │
    │    │ turn (DB)        │
    │    │ persist_comple-  │
    │    │ tion (DB)        │
    │    │ store.checkpoint │
    │    │ EventLog:        │
    │    │  interview_      │
    │    │  finished        │
    │    └────┬─────────────┘
    │         │
    │    WS {type: "report"}
    │
    ▼
 difficulty_governor (LLM first 4 turns, then conditional; cheap tier)
    │
    ▼
 EventLog: difficulty_changed
    │
    ▼
 question_generator_node
    │
    ▼
 EventLog: question_asked
    │
    ▼
 persist_answer_turn → store.checkpoint → WS {type: "evaluation"}
```

### Hypothesis Lifecycle

```
Generate (from profile + taxonomy)
    │
    ▼
UNTESTED ──── first evidence ────► TESTING
    │                                    │
    │                              high confidence (>= 0.8)
    │                                    │
    │                                    ▼
    │                               CONFIRMED
    │                                    │
    │                              contradicting evidence
    │                              + low confidence (<= 0.2)
    │                                    │
    │                                    ▼
    │                               REFUTED
    │
    └──► next_target() picks by expected information gain (EIG):
         1. untested → EIG = 1.0 (max entropy — coverage first)
         2. probed    → EIG = H(p) = −p·log₂p − (1−p)·log₂(1−p);
                        the hypothesis closest to p = 0.5 wins
         3. everything settled (confirmed ≥ 0.9) → deep_probe fallback
            (highest confidence) so a target is always returned while any
            non-refuted hypothesis remains

         confidence is a real posterior: prior PRIOR_CONFIDENCE = 0.5, moved by
         the evidence delta each turn. The selected target carries
         information_gain + selection_reason (explainability for free).
```

---

## Persistence & Write-Back

All best-effort DB writes live in `app/engine/persistence.py` (Phase 1 split),
called by the engine modules; the DB call never raises.

| Action | When | Backend | DB effect |
|--------|------|---------|-----------|
| Session row | entry point | `candidates/service.py` / `marketplace/service.py` | `interview_sessions` (engine_version="v4") |
| State checkpoint | every answer turn + finalization | `store.checkpoint()` (v4_session_store.py) | `v4_session_state` (upsert, bumps `state_version`) |
| Evidence | every answer | `persist_evidence` → `EvidenceRepository` | `evidence_store` (incl. `evidence_metadata` quality dict) |
| Q/A + evaluation | every answer | `persist_answer_turn` (app/engine/persistence.py) | `interview_messages` + `interview_evaluations` |
| Completion | on finish | `persist_completion` (app/engine/persistence.py) | `interview_sessions` (status, final_score) |
| V5 brain snapshot | every answer + finish (opt-in) | `persist_v5_snapshot` → `V5BrainPersister` | `interview_brain` + `evidence_graphs` + `interview_timelines` |
| Pipeline event | every pipeline stage | `EventLog.append()` (event_log.py) | `interview_events` (append-only, best-effort) |

Repositories are obtained from `app/services/repositories.py` (`get_session_repo`,
`get_message_repo`, `get_evaluation_repo`) — the same repos serve the report route.

---

## Event Log (Tier 3 Observability)

Append-only log of every pipeline stage, stored in `interview_events`. Used for
debugging, replay, and audit — never raises (best-effort by design, exactly the
same contract as `app/engine/persistence.py`).

```python
from app.services.event_log import get_event_log
await get_event_log().append(session_id, "evaluation_done", {...})
```

### Schema (migration `a7f3c2e1b9d4`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | bigserial PK | |
| `session_id` | uuid FK → interview_sessions | ON DELETE CASCADE |
| `seq` | int | per-session monotonic, UNIQUE(session_id, seq) |
| `event_type` | text | e.g. `session_started`, `answer_received` |
| `payload` | jsonb | stage-specific data |
| `created_at` | timestamptz | default now() |

### Event Types

| Event | Hook Location | Payload Highlights |
|-------|---------------|-------------------|
| `session_started` | `_start_v4_engine` (interview_ws.py:128) | style, competencies, taxonomy, domain |
| `answer_received` | `process_answer` entry (app/engine/answer_processor.py:37) | length, injection_signals |
| `evaluation_done` | after `explainable_scoring_node` (answer_processor.py:66) | unified_evaluation, evaluation_score, score_reasons |
| `evidence_added` | after `evidence_extractor_node` (answer_processor.py:72) | evidence_count, competency_summary |
| `difficulty_changed` | after `difficulty_governor` (app/engine/routing.py:195) | prev, new level |
| `action_decided` | after `reflection_engine` (routing.py:36) | reflection_action |
| `director_decided` | after `director_controller` (routing.py:46) | action, reason |
| `question_selected` | after `hypothesis_node` (routing.py:87; interview_ws.py:166) | target_hypothesis_id, competency, status, selection_reason, information_gain |
| `hypothesis_updated` | after `hypothesis_node`, only when changed (routing.py:99) | before/after snapshots (confidence, status, evidence counts) |
| `question_asked` | after `question_generator_node` (routing.py:157) | question_number, phase, difficulty |
| `interview_finished` | `finalize_session` (app/engine/decision.py:53) | final_score, hiring_recommendation |

---

## Session Store Backends

The session store (`app/services/v4_session_store.py`) is the shared read/write
layer for live `InterviewState`. Both backends expose an identical API so the rest
of the codebase is backend-agnostic.

### MemoryV4SessionStore (default)

- In-process dict, write-behind to Postgres `v4_session_state` (JSONB)
- `flush()` at shutdown writes dirty sessions
- `checkpoint()` writes through immediately (upserts, bumps `state_version`)
- Eviction at startup (24h max age)
- Used when `SESSION_STORE_BACKEND=memory` (default) or Redis unavailable

### RedisV4SessionStore

- Redis key `aura:sess:{session_id}`, JSON value, TTL 24h refreshed on `set()`
- `checkpoint()` writes through to Postgres (redis = hot tier; Postgres = durable)
- Lazy hydrates from Postgres on `get`-miss (resume works across replicas)
- `pop()` deletes from both Redis and Postgres
- `list_active()` / `count()` via Redis `SCAN` / `dbsize()`
- **Degrades to in-process dict** if Redis is unavailable (never raises)
- Used when `SESSION_STORE_BACKEND=redis` + `REDIS_URL` is set

### Config

| Env var | Values | Default | Notes |
|---------|--------|---------|-------|
| `SESSION_STORE_BACKEND` | `memory` / `redis` | `memory` | No deploy change to stay on existing behavior |
| `REDIS_URL` | Redis connection URL | (none) | Required when backend = redis; same value as `cache.py` |

---

## LLM Tiering & Cost Control

`app/models/llm.py` holds the tier registry; `app/services/llm_service.py`
routes every invocation through it.

| Tier | Models (fallback chain) | Used by |
|------|-------------------------|---------|
| `cheap` | `llama-3.1-8b-instant` (Groq) → local `one` → strong-chain fallback | candidate evaluator, difficulty governor, question generator, resume analyzer, company intelligence, blueprint builder |
| `strong` | `llama-3.3-70b-versatile` (Groq) → local `one` → `openrouter/auto-beta` | synthesis, hiring decision (strategy planner stays on the default strong) |
| `openrouter` (default) | provider from `LLM_PROVIDER` env | anything calling without a tier |

`get_llm(name)` resolves a tier to a live instance (default provider
`LLM_PROVIDER` env, default `"openrouter"`). `invoke` / `invoke_stream` /
`invoke_structured` all accept a `tier=` kwarg, and the LLM response cache key
includes the tier so cheap/strong calls never share cache entries.

This is the cost lever behind the Phase 6 work: high-volume, low-judgment calls
(evaluation, governing, question generation) run on the cheap chain while the
few high-judgment calls (synthesis, hiring decision) stay on strong models.
