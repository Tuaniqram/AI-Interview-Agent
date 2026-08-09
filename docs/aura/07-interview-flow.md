# 07 — Interview flow (end to end)

> Last updated: 2026-08-09 · Tag: [AURA-1.2][T2-scoring]

## Sequence (demo_autopilot → brain view)

```
1. POST /api/v1/auth/login                          org login → org_token, org_id
2. GET  /api/v1/departments                         first department
3. GET/POST /api/v1/marketplace/org/{org}/interviews  reuse or create listing
4. POST /api/v1/candidates/login (or /register)     candidate_token
5. GET  /api/v1/candidates/me
6. POST /api/v1/marketplace/interviews/{id}/start   → session_id
7. WS   /ws/interview/{sid}?token=<cand_jwt>
   ├─ {type:"start_interview"}          → {type:"question"}
   ├─ loop: {type:"submit_answer", candidate_answer}
   │    → {type:"status", phase:"evaluating"}
   │    → {type:"evaluation", ..., brain}  OR  {type:"report", ...}
   │    → {type:"request_question"}     → {type:"question"}
8. GET  /interviews/{sid}/summary                     transcript + v4 verdict
9. GET  /api/v1/intelligence/brain/{sid}              brain view (brain_view.json)
```

## Session start (server side)

WS `start_interview` handler builds the seeded state dict:
1. Loads the `interview_sessions` row, resolves org + department.
2. `resolve_competencies(...)` → taxonomy (scorecard → template → AI profiler → default).
3. Loads candidate profile/resume.
4. Builds/loads the **company brain** (`get_or_build_company_brain`).
5. `engine.start_session(state, build_intelligence=True)`.

`lifecycle.start_session`:
- Injects the intelligence bundle (company_brain, interview_blueprint,
  candidate_brain, initial_hypotheses, evidence_requirements, candidate_assessment).
- Normalizes competency ids (aliases → canonical taxonomy ids).
- Runs the node chain:
  `session_init → department_context → candidate_profile → competency_planner →
  strategy_brain → hypothesis_node → question_generator`.
- Emits `question_selected` event (target hypothesis, competency, reason,
  information gain), persists the first brain snapshot, returns the opening question.

## Answer loop (server side)

`engine.process_answer(sid, answer)` → `answer_processor.process_answer`:
1. **Sanitize** — `sanitize_user_input` + prompt-injection scan; log `answer_received`.
2. **Budget check** — if `question_number >= max_questions`, finalize.
3. Append Q/A to `conversation_history`.
4. **Evaluate** — `unified_evaluator_node` scores the answer across the
   family's **active dimensions** (T2): `active_dimensions(category)` decides
   which of the 7 rubric dimensions count, and `{{rubric}}` +
   `{{primary_dimension}}` are rendered into the prompt from
   `app/data/rubrics.py`.
5. **Evidence** — `evidence_extractor_node` extracts typed evidence records.
6. **Score** — `explainable_scoring_node` recomputes the composite
   deterministically; `reconcile_composite` resolves importance weights per
   family via `dimension_weights(category)` (tech = `technical`-led, non-tech
   families = `domain`-led with `technical` zeroed) + optional calibration.
7. **Persist** — `persist_evidence` writes evidence/competency summary/hypotheses/events.
8. **Route** — `route_answer`:
   - reflection (`reflection_engine`)
   - action director (`director.py`) picks CONTINUE / PROBE / CHALLENGE / CLOSE
   - difficulty governor (`difficulty_engine.difficulty_governor`) → delta −1/0/+1
   - `hypothesis_node` updates hypotheses → `question_generator_node` → next question.

Frames to the client: `status/evaluating` → `evaluation` (result + assembled
`brain` layers) or `report` when finished. The client then sends
`request_question` for the next question frame.

## Finish

When the budget is exhausted (or sufficiency/early-termination reached),
`finalize_session` runs: synthesis → hiring decision → decision review → report.
The `report` frame carries the verdict, score, rationale and next steps; the
session is persisted as `completed` with `final_score`.

## Brain view (read)

`GET /api/v1/intelligence/brain/{sid}` hydrates the persisted brain and returns:
`interview_brain` (the assembled layers), `evidence_graph` (nodes/edges), and
`timeline` (replayed `interview_timeline` events). The sample captured at
`D:\UnityTemp\opencode\aura-run\brain_view.json` is this endpoint's output.
