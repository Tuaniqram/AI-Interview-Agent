# 02 — Architecture

> Last updated: 2026-08-09 · Tag: [AURA-1.0-baseline]

## Layers

```
                    ┌────────────────────────────────────────────────┐
   Entry points     │ app/api/interview_ws.py  (WS /ws/interview/{sid}) │
                    │ app/api/v1/* (auth, departments, candidates,      │
                    │  marketplace, intelligence)                       │
                    └───────────────────────┬────────────────────────┘
                                            │ session dicts
                    ┌───────────────────────▼────────────────────────┐
   Engine core      │ app/engine/   (V5 orchestration)                │
   (coordination)   │  engine.py · lifecycle · answer_processor ·      │
                    │  routing · decision · persistence · builders     │
                    └───────────────────────┬────────────────────────┘
                                            │ plain dicts (V4 boundary)
                    ┌───────────────────────▼────────────────────────┐
   Agents           │ app/agents/  (nodes: init → planning →           │
   (V4-style nodes) │  reasoning → generation → evaluation → decision) │
                    └───────────────────────┬────────────────────────┘
                                            │ reconciling brain
                    ┌───────────────────────▼────────────────────────┐
   Brain layers     │ app/brain/  (V5 deterministic intelligence)      │
                    │  assembler · role · company · hypotheses ·      │
                    │  evidence · calibration · memory · contradiction │
                    └───────────────────────┬────────────────────────┘
                                            │ intelligence bundle
                    ┌───────────────────────▼────────────────────────┐
   Intelligence     │ app/intelligence/ (V5 company/candidate bundles) │
                    │  profiler · blueprint · company · candidate ·     │
                    │  persist · resume/scorecard/resolver             │
                    └───────────────────────┬────────────────────────┘
                                            │ persistence (best-effort)
                    ┌───────────────────────▼────────────────────────┐
   Services         │ app/services/  store · persister · events · LLM  │
                    │ app/repositories/ · app/models/db.py             │
                    └────────────────────────────────────────────────┘
```

## Module map (engine touch points)

| Module | Role |
|---|---|
| `app/engine/engine.py` | `InterviewEngine` coordinator; `start_session` / `process_answer` / `get_brain` |
| `app/engine/lifecycle.py` | Session start chain: inject intelligence → init → planning → hypotheses → first question |
| `app/engine/answer_processor.py` | Per-answer: sanitize → evaluate → evidence → score → route |
| `app/engine/routing.py` | Reflection → action director → difficulty governor → next question |
| `app/engine/decision.py` | Finalize: synthesis → hiring decision → report |
| `app/engine/persistence.py` | Best-effort DB + V5 brain snapshot writes |
| `app/engine/builders.py` | Response payloads (question / evaluation / report) |
| `app/core/interview_brain.py` | `InterviewBrain` — authoritative per-session state |
| `app/core/interview_state.py` | dict ↔ brain sync helpers |

## Data flow (per session)

1. **Start** — WS `start_interview` → `engine.start_session(state, build_intelligence=True)`.
   `lifecycle.start_session` builds/merges the intelligence bundle
   (`company_brain`, `interview_blueprint`, `candidate_brain`,
   `initial_hypotheses`, `evidence_requirements`, `candidate_assessment`),
   normalizes competency ids, then runs nodes: `session_init → department_context
   → candidate_profile → competency_planner → strategy_brain → hypothesis_node →
   question_generator`. First `{type: question}` frame is emitted.
2. **Turn** — WS `submit_answer` → `engine.process_answer(sid, answer)`.
   `answer_processor.process_answer`: sanitize + injection scan → append
   conversation → `unified_evaluator_node` → `evidence_extractor_node` →
   `explainable_scoring_node` → `persist_evidence` → `route_answer`
   (reflection → director → difficulty governor → `question_generator`).
   Frames: `{type: status/evaluating}`, then `{type: evaluation, ...}` (with the
   assembled brain) or `{type: report, ...}` when complete.
3. **Finish** — When question budget/sufficiency is met,
   `answer_processor`/`routing` call `finalize_session`: synthesis → hiring
   decision → decision review → report. `{type: report}` frame carries the full
   result; the session is persisted as `completed`.
4. **Read** — `GET /interviews/{sid}/summary` (transcript + v4 verdict) and
   `GET /api/v1/intelligence/brain/{sid}` (assembled `interview_brain`,
   `evidence_graph`, `timeline`).

## Persistence design

Best-effort everywhere. `app/engine/persistence.py` writes the evidence store,
competency summary, hypotheses, events, and the V5 snapshot
(`app/services/v5_brain_persister.py` → `interview_brain`, `evidence_graph`,
`interview_timeline`). Failures are logged and swallowed — the in-memory store
(`app/services/v4_session_store.py`) plus its Postgres checkpoint
(`v4_session_state`) keep the session alive.
