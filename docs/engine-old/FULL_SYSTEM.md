# AURA Interview Agent — Full System Guide

This document is the single reference for the **whole system**: marketplace
listings → scorecards → interview lifecycle (start → answer loop → finish) →
post-interview analytics, the complete REST + WebSocket API surface, and the
V5 interview engine internals.

Related docs:
- `docs/api.md` — the **start flow** in depth (practice + listing → WS boot, frontend + backend).
- `docs/ENGINE_ARCHITECTURE.md` — the V5 engine internals (nodes, prompts, agent packages).
- `docs/AURA_V5_ROADMAP.md` — migration history and planned work.

---

## 1. System overview

Two personas operate the platform:

| Persona | Authenticates as | Surface |
| --- | --- | --- |
| **Recruiter / org member** | `User` (JWT via `/api/v1/auth/*`) | orgs, departments, templates, listings, scheduling, scorecards, analytics, ranking, audit logs |
| **Candidate** | `CandidateProfile` (JWT via `/api/v1/candidates/*`) | practice, saved listings, own interviews, competency scores, resume |

Engine versions: `InterviewSession.engine_version` defaults to `"v3"`, but every
live flow seeds `"v4"`/`"v5"` and runs through the **WebSocket** protocol. The
v3 legacy engine was archived and later removed (Phase 8 dead-code pass); only
the summary endpoint (`/interviews/{session_id}/summary`) survives from the old
REST pipeline.

### Core split

```
REST  ── session seeding / listing / scorecards / admin (POST /start, /practice/start, …)
WS    ── all live interview traffic (ws://host/ws/interview/{session_id})
Store ── in-memory v4 session store holds engine state, keyed by session_id
DB    ── interview_sessions row is the anchor (job_role, department_id, engine_version)
```

The DB row and the in-memory store live under the **same `session_id`**. The DB
row is created over REST; the engine state is seeded into the store at the same
time and then evolved by the engine over the WebSocket.

---

## 2. End-to-end flows

```
┌───────────────────────────── RECRUITER ─────────────────────────────┐
│  1. create org → 2. add members → 3. create department              │
│  4. build scorecard template                                        │
│  5. build interview template (ties scorecard_template_id)           │
│  6. publish a public listing (POST /marketplace/interviews)         │
│  7. share link (token) or let candidates browse the marketplace     │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                        candidate starts (POST start / token start)
                                        ▼
┌───────────────────────────── CANDIDATE ─────────────────────────────┐
│  POST /api/v1/marketplace/interviews/{id}/start      (public)      │
│  POST /api/v1/public/interviews/{token}/start        (share link)  │
│  POST /api/v1/candidates/practice/start              (practice)    │
│      → creates InterviewSession + seeds v4 store + returns         │
│        { session_id }                                               │
│  navigate(/interview/{session_id})                                  │
│      → WS connect + {type:"start_interview"}                        │
│      → engine boots (intelligence + start node chain)               │
│      → {type:"question"} Q1                                         │
│      → loop: {type:"submit_answer"} → {type:"evaluation"}           │
│      → … until reflection says finish → {type:"report"}             │
│      → session row marked completed, final_score written            │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                    completed
                                        ▼
┌───────────────────────────── POST-INTERVIEW ────────────────────────┐
│  GET  /interviews/{session_id}/summary           (candidate report) │
│  POST /orgs/{org_id}/scorecards/{t}/sessions/{s}/calculate          │
│  GET  /orgs/{org_id}/candidates/ranking          (recruiter)        │
│  GET  /orgs/{org_id}/candidates/ranking/summary  (recruiter)        │
│  GET  /api/v1/analytics/*                        (recruiter)        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Marketplace / listings

Model: `PublicInterview` (`app/models/db.py:570`) — a job listing that exposes
an interview to the public. Backed by `app/api/v1/marketplace.py` (org-owned
CRUD + public browse) and `app/api/v1/public.py` (token start).

### 3.1 Publish a listing (org owner)

`POST /api/v1/marketplace/interviews` (`app/api/v1/marketplace.py:65`) →
`create_public_interview` (`app/marketplace/service.py:318`):

1. Creates the `PublicInterview` row (`is_open=True`, `style_name="AURA"`,
   `token=uuid4().hex`, `verification_method="none"`).
2. Fires a background task `generate_rich_description` (AI description).
3. Writes an `marketplace.create` audit log.
4. Returns `OrgPublicInterviewResponse` (includes the internal `token` for the
   share link and the `template_id` used to resolve competencies).

Body — `CreatePublicInterviewRequest` (`app/marketplace/schemas.py:62`):
`title`, `department_id`, `description?`, `interview_mode="typing"`,
`max_candidates?`, `skills_required?`, `style_name="STANDARD"`,
`template_id?`, `starts_at?`, `expires_at?`.

### 3.2 Public browse (no auth)

| Endpoint | Purpose | File:line |
| --- | --- | --- |
| `GET /api/v1/marketplace/organizations` | Active orgs with open listings; `search`, `modes`, `expiry` filters | `marketplace.py:33` → `service.py:38` |
| `GET /api/v1/marketplace/organizations/{slug}` | Org profile + its open interviews | `marketplace.py:43` → `service.py:103` |
| `GET /api/v1/marketplace/interviews/{interview_id}` | One public interview | `marketplace.py:48` → `service.py:158` |

### 3.3 Org CRUD

| Endpoint | Role | File:line |
| --- | --- | --- |
| `GET /api/v1/marketplace/org/{org_id}/interviews` | owner/member/viewer | `marketplace.py:80` → `service.py:374` |
| `PUT /api/v1/marketplace/interviews/{interview_id}` | owner | `marketplace.py:89` → `service.py:396` |
| `DELETE /api/v1/marketplace/interviews/{interview_id}` (204) | owner | `marketplace.py:109` → `service.py:433` |

`update_public_interview` force-pins `style_name="AURA"` and regenerates the
rich description when title/skills change (`service.py:412-418`).

### 3.4 Start an interview from a listing

Two entry points call the **same service** `start_public_interview`
(`app/marketplace/service.py:199`):

1. `POST /api/v1/marketplace/interviews/{interview_id}/start` (`marketplace.py:53`, no auth).
2. `POST /api/v1/public/interviews/{token}/start` (`public.py:16`, no auth — validates `is_open` + `starts_at`/`expires_at` window, then audits `public_interview.start`).

The service does, in order:

1. Loads the open `PublicInterview` (404 otherwise).
2. Resolves `scorecard_template_id` from the linked `InterviewTemplate` (`service.py:211-219`).
3. Creates `InterviewSession(session_type="public", interaction_mode=pi.interview_mode, engine_version="v4", scorecard_template_id=…)` (`service.py:221`).
4. Links the session to an existing `CandidateProfile` when `candidate_email`
   matches (G4 requirement, `service.py:233-241`).
5. Resolves competencies via `resolve_competencies(scorecard_template_id, department_id)`
   (`app/data/competency_resolver.py:118`) then `taxonomy_for_state`; seeds the
   AURA state dict into the v4 store under `session_id` (`service.py:254-301`).
6. Records a `PublicInterviewSubmission` row (email/name) and returns
   `{session_id, token}` (`service.py:303-315`).

**Competency resolution order** (first non-empty wins, `competency_resolver.py:7-10`):
scorecard template → interview template (newest per department) → default taxonomy.

---

## 4. Practice (candidate)

`POST /api/v1/candidates/practice/start` (`app/api/v1/candidates.py:270`,
`require_verified_candidate`) → `start_practice` (`app/candidates/service.py:274`):

1. Creates `InterviewSession(session_type="mock", interaction_mode="typing",
   engine_version="v4", total_questions=num_questions)` + `CandidateSession` row.
2. Seeds the v4 store with AURA state using the candidate's `profile_data`
   strengths/weaknesses (`service.py:311-363`).
3. Returns `PracticeStartResponse {session_id, job_role, total_questions, interview_style}`.

Body — `PracticeStartRequest`: `job_role`, `difficulty`, `tech_stack?`,
`num_questions`, `interview_style`.

---

## 5. Interview lifecycle (WebSocket)

### 5.1 Wire protocol

Endpoint: `ws://host/ws/interview/{session_id}?token={candidate_token}`
(`app/api/interview_ws.py:257`). Token is optional; when present and of type
`candidate_access`, the socket verifies session ownership (`interview_ws.py:86`).

Every client request carries an `_id`; the server echoes it back so the client
can resolve the matching response (`_send_id`, `interview_ws.py:102`).

| Client → Server | Server → Client | Notes |
| --- | --- | --- |
| `{_id, type:"start_interview", session_id}` | `{_id, type:"question", …start_response}` | Boots (or resumes) the V5 engine. |
| `{_id, type:"request_question", session_id}` | `{_id, type:"question", …}` | Idempotent resend of current question. |
| `{_id, type:"submit_answer", candidate_answer}` | `{type:"status", phase:"evaluating"}` → `{type:"status", phase:"question_ready"}` + `{_id, type:"evaluation", …answer_response}` | One answer; finished sessions return `{type:"report", …}` instead. |
| `{_id, type:"get_status", session_id}` | `{_id, type:"status_snapshot", …state_response}` | Resume/reconnect check. |
| `{_id, type:"ping"}` | `{_id, type:"pong"}` | Keep-alive. |
| — (server push) | `{type:"connected", session_id}` | Sent immediately after accept. |
| — | `{type:"error", detail}` | Any failure path. |

Stale connections are reaped every 60s after 300s of inactivity
(`interview_ws.py:62-70`).

### 5.2 Boot (`start_interview`)

`_start_v4_engine` (`interview_ws.py:170`):

1. If the store already has state → resume (`build_start_response`).
2. Otherwise load the DB session row (404 → `SessionNotFoundException`), resolve
   the **AURA** style + competency taxonomy from the department
   (`resolve_competencies`), and load candidate profile/resume text.
3. Build the full AURA state dict (the same 40-field shape seeded by
   `marketplace/service.py` and `candidates/service.py`).
4. `InterviewEngine(store, v5_persister).start_session(state, build_intelligence=True, company_brain=cache_lookup)`
   (`app/engine/lifecycle.py:23`), where `company_brain` comes from
   `get_or_build_company_brain(department_id, job_role)` (`app/intelligence/company_cache.py`).
5. Reply: `{type:"question", **build_start_response(session_id, brain)}`.

`start_session` (idempotent — an existing session resumes without re-running the
chain) runs the start node chain over the reconciled `InterviewBrain`:

```
session_init_node → department_context_node → candidate_profile_node →
competency_planner_node → strategy_brain_node → hypothesis_node →
question_generator_node
```

with an optional `build_interview_intelligence` pass injected before the chain
(when no intelligence kwargs are supplied). Supplied `**intelligence` kwargs
(`company_brain`, `interview_blueprint`, `candidate_brain`,
`initial_hypotheses`, `evidence_requirements`, `candidate_assessment`) are merged
onto the brain directly; the automatic build is **best-effort** — a failure is
logged and the session proceeds without the bundle. It appends
`question_selected` and `session_started` events, then persists the brain to the
store + checkpoint.

### 5.3 Answer loop (`submit_answer`)

`InterviewEngine.process_answer(session_id, answer)` → `app/engine/answer_processor.py:17`:

1. Sanitizes the input and runs prompt-injection detection (`app/utils/input_sanitizer.py`).
2. Guards on `question_number >= max_questions` → `finalize_session`.
3. Appends the (question, answer) pair to `conversation_history`.
4. `unified_evaluator_node` (evaluates dimensions → `unified_evaluation`,
   `evaluation_score`) → `evidence_extractor_node` (→ `evidence_store`,
   `competency_summary`, now with **quality annotation**) →
   `explainable_scoring_node` (deterministic **score_contributions + score_reasons**).
   Evidence rows are flushed to the `evidence_store` DB via `persist_evidence`.
5. Routes through the **unified pipeline** (`app/engine/routing.py:174`) — all
   flow types share it:
   `reflect_and_select` (reflection → director → hypothesis selection) →
   conditional-LLM difficulty governor (LLM forced for the first 4 turns, then
   only when the last read is not decisive) → question generation → persist turn
   → checkpoint brain → persist V5 snapshot.

`reflect_and_select` (`routing.py:18`) runs `reflection_engine`, which now feeds
richer inputs into the deterministic **director** (`app/agents/decision/director.py`)
that decides the action:
- `FINISH` → `finalize_session` (short-circuit);
- `CHANGE_COMPETENCY` → re-plan + re-hypothesize (`competency_planner_node`,
  `route_after_planner`, `hypothesis_node`);
- `PROBE` / `CONTINUE` → `hypothesis_node` runs again on the new evidence.

Then `emit_question_and_persist` (`routing.py:142`) runs
`question_generator_node`, persists the Q/A turn to the DB (`persist_answer_turn`),
checkpoints the brain, and returns `build_answer_response`.

The WS layer (`interview_ws.py:314-342`) sends `status evaluating` first, then
either `evaluation` + `status question_ready` (session continues) or `report`
(`completed = status=="completed" or interview_complete`).

### 5.4 Finish (`finalize_session`, `app/engine/decision.py:21`)

1. `synthesis_node` (best-effort) → `hiring_decision_node` →
   **`decision_review_node`** (self-review pass that can demote the draft and
   flag issues before anything is persisted).
2. `persist_answer_turn` + `persist_completion` (writes `final_score`,
   `final_feedback`, `status="completed"`, `ended_at`, `engine_version="v5"` —
   `session_repository.complete_session`).
3. Store + checkpoint + version bump.
4. `build_report_response(brain)` + `interview_complete=True`; persists V5
   snapshot; logs `interview_finished` event; returns the report.

The report frame (`build_report_response`, `app/engine/builders.py:166`) contains:
`status:"completed"`, `hiring_recommendation {verdict, confidence, composite_score,
coverage_ratio}`, per-competency `competency_summary {average_score, evidence_count,
gap}`, `evidence_collected`, `questions_asked`, `hypothesis_outcomes`,
`evidence_graph {competency_nodes, evidence_edges}`, `difficulty_profile`,
`hiring_decision`.

### 5.5 Resume / status

`get_status` → `build_state_response` (`builders.py:135`): question number,
current question, `interview_complete`, difficulty, evidence count,
`competency_coverage`, `hypothesis_summary`, contradictions, hiring recommendation,
evaluation score.

---

## 6. Scorecards

### 6.1 Concepts

- **`ScorecardTemplate`** (`app/models/db.py:990`): org-owned list of
  `CompetencyDef {id, name, category, weight, max_score}` (stored as JSONB).
- **`ScorecardResult`** (`db.py:1017`): computed per `(session_id, template_id)` —
  `scores` (per-competency breakdown) + `weighted_score`.
- **`InterviewTemplate`** (`db.py:389`) carries an optional `scorecard_template_id`
  and is what listings link against; when a public session starts, the scorecard
  id is copied onto the `InterviewSession.scorecard_template_id` (`db.py:291`).
- **`EvidenceStore`** (`db.py:796`): per-question evidence rows
  `(session_id, competency, dimension, score, evidence_text, source_question,
  question_number, confidence)` written by the engine.

### 6.2 Template CRUD — `app/api/v1/scorecards.py`

Router prefix: `/orgs/{org_id}/scorecards`.

| Endpoint | Role | File:line |
| --- | --- | --- |
| `GET ""` list templates | owner/member | `scorecards.py:32` |
| `POST ""` create (201) | owner | `scorecards.py:46` |
| `GET /{template_id}` | owner/member | `scorecards.py:65` |
| `PUT /{template_id}` | owner | `scorecards.py:84` |
| `DELETE /{template_id}` (204) | owner | `scorecards.py:110` |
| `POST /{template_id}/sessions/{session_id}/calculate` | owner/member | `scorecards.py:130` |
| `GET /sessions/{session_id}` | owner/member | `scorecards.py:144` |

Body for create/update — `ScorecardTemplateCreate` (`app/scorecards/schemas.py:18`):
`name`, `competencies: [CompetencyDef]`.

### 6.3 Calculation algorithm

`calculate_scorecard_for_session(db, session_id, template_id)`
(`app/scorecards/service.py:20`):

1. Load the template; group `EvidenceStore` rows by competency.
2. Per `CompetencyDef`: `raw_avg = mean(evidence scores)`;
   `normalized = (raw_avg / max_score) * 10`; `weighted = normalized * weight`.
3. `weighted_score = Σ(normalized·weight) / Σ(weight)`.
4. Upserts the `ScorecardResult` and returns `ScorecardResultResponse {id,
   session_id, template_id, scores, weighted_score, created_at}`.

`scores[comp_id]` shape: `{raw_avg, normalized, weight, weighted, evidence_count}`.

`auto_calculate_on_complete(session_id, scorecard_template_id)`
(`service.py:97`) is a fire-and-forget hook for automatic scoring at interview
completion (currently called explicitly by the calculate endpoint).

---

## 7. Post-interview

### 7.1 Candidate report

`GET /interviews/{session_id}/summary` (`app/api/interview_agent.py:166`,
optional candidate auth, ownership enforced at `interview_agent.py:35`).

For v4/v5 sessions it merges the legacy DB-based summary with engine extras
read from the durable `interview_brain` snapshot (`_get_engine_summary`,
`interview_agent.py:131`): `v4_verdict`, `v4_confidence`,
`v4_composite_score`, `v4_evidence_count`, `v4_questions_asked`,
`v4_competency_summary`, `v4_hypothesis_outcomes`.

### 7.2 Candidate ranking

`app/api/v1/candidate_ranking.py`, prefix `/orgs/{org_id}/candidates`,
owner/member.

| Endpoint | Purpose |
| --- | --- |
| `GET /ranking` | Ranked completed sessions by `final_score` desc, joined to candidate + department; includes `weighted_score` from `ScorecardResult`. Filters: `department_id`, `job_role`. |
| `GET /ranking/summary` | Aggregated `total_candidates`, `average_score`, `max_score`, `min_score` grouped by `(job_role, department)`. |
| `GET /export` | CSV download of the ranking. |

### 7.3 Analytics

`app/api/v1/analytics.py`, prefix `/analytics`, owner/member/viewer.
`org_id` resolved via `resolve_org_id`.

| Endpoint | Returns |
| --- | --- |
| `GET /overview` | `total_departments`, `total_sessions`, `active_sessions`, `completed_sessions`, `average_score`, `completion_rate`. |
| `GET /scores/trend` | Per-day `{date, avg_score, count}`. |
| `GET /scores/distribution` | Buckets `0-2…9-10` with counts. |
| `GET /sessions/by-department` | `{department_id, name, session_count, avg_score}`. |
| `GET /sessions/by-role` | `{job_role, count, avg_score}`. |

### 7.4 Candidate-side views

`app/api/v1/candidates.py` (verified-candidate auth unless noted):

| Endpoint | Purpose | File:line |
| --- | --- | --- |
| `GET /interviews` | List own sessions | `candidates.py:163` |
| `GET /interviews/{interview_id}` | Own-session detail (score, feedback, dept) | `candidates.py:171` |
| `GET /stats` | `total_interviews`, `completed`, `active`, `average_score` | `candidates.py:180` |
| `GET /competency-scores` | Per-competency `{competency, name, category, average_score, evidence_count}` from `EvidenceStore` | `candidates.py:188` |
| `POST /saved-listings/{listing_id}` | Save a listing | `candidates.py:196` |
| `DELETE /saved-listings/{listing_id}` | Unsave | `candidates.py:220` |
| `GET /saved-listings` | List saved listings w/ org info | `candidates.py:240` |
| `POST /me/resume` | Upload + parse resume (merges skills) | `candidates.py:351` |
| `GET /{candidate_id}/resume` | Download resume (owner/member) | `candidates.py:383` |

---

## 8. Full REST API reference

All v1 routers are mounted under `prefix="/api/v1"` in `app/main.py:82-95`.
`interview_agent`, `interview_ws` and `system` are mounted without
a prefix. Rate limits (`main.py:114-132`): 20 req/min on auth endpoints, 120
req/min on `/api/v1/`, `/interviews/`, `/`.

### 8.1 Auth — `/api/v1/auth/*` (`app/api/v1/auth.py`)

| Method + Path | Purpose | File:line |
| --- | --- | --- |
| `POST /auth/register` | Create `User` account | `auth.py:34` |
| `POST /auth/login` | Login | `auth.py:39` |
| `POST /auth/google` | Google OAuth login | `auth.py:44` |
| `POST /auth/refresh` | Rotate refresh token | `auth.py:51` |
| `POST /auth/logout` (204) | Revoke | `auth.py:56` |
| `GET /auth/me` | Current user | `auth.py:61` |
| `POST /auth/forgot-password` | Send reset email | `auth.py:82` |
| `POST /auth/reset-password` | Set new password | `auth.py:116` |

### 8.2 Orgs — `/api/v1/orgs/*` (`app/api/v1/orgs.py`)

| Method + Path | Role | File:line |
| --- | --- | --- |
| `POST /orgs` | authenticated | `orgs.py:40` |
| `GET /orgs/{org_id}` | owner/member/viewer | `orgs.py:49` |
| `PATCH /orgs/{org_id}` | owner | `orgs.py:59` |
| `GET /orgs/{org_id}/members` | owner/member/viewer | `orgs.py:70` |
| `POST /orgs/{org_id}/members` | owner | `orgs.py:82` |
| `POST /orgs/{org_id}/members/by-email` | owner | `orgs.py:93` |
| `PATCH /orgs/{org_id}/members/{member_id}` | owner | `orgs.py:104` |
| `DELETE /orgs/{org_id}/members/{member_id}` (204) | owner | `orgs.py:116` |
| `GET /orgs/{org_id}/templates` | owner/member/viewer | `orgs.py:127` |
| `POST /orgs/{org_id}/invite` | authenticated | `orgs.py:164` |
| `GET /orgs/invitations/{token}` | none | `orgs.py:174` |
| `POST /orgs/invitations/{token}/accept` | authenticated | `orgs.py:182` |

### 8.3 Departments — `/api/v1/departments/*` (`app/api/v1/departments.py`)

`GET/POST ""`; `GET/PATCH/DELETE /{department_id}`; `GET /{id}/sessions`;
`GET/POST/DELETE /{id}/documents…`; and the interview-template CRUD:
`GET/POST /{id}/templates`, `GET/PUT/DELETE /{id}/templates/{template_id}`
(creates/updates `InterviewTemplate` incl. `scorecard_template_id`,
`departments.py:305-327, 372, 426-427`).

### 8.4 Scheduling — `/api/v1/scheduling/*` (`app/api/v1/scheduling.py`)

| Method + Path | Role | File:line |
| --- | --- | --- |
| `POST /scheduling/slots` | owner | `scheduling.py:28` |
| `GET /scheduling/slots` | owner/member/viewer | `scheduling.py:38` |
| `POST /scheduling/availability` | owner/member | `scheduling.py:47` |
| `GET /scheduling/available` | none (public calendar via `X-Org-Id`) | `scheduling.py:57` |
| `POST /scheduling/book` | owner/member | `scheduling.py:65` |
| `POST /scheduling/bookings/{booking_id}/cancel` (204) | owner/member | `scheduling.py:74` |

### 8.5 Admin — `/api/v1/admin/*` (`app/api/v1/admin.py`)

`GET /admin/stats`, `GET /admin/organizations`, `POST /admin/organizations/{org_id}/toggle-suspend`,
`GET /admin/users` (`admin.py:21,29,38,48`).

### 8.6 Invitations — `/api/v1/invitations/*` (`app/api/v1/invitations.py`)

Candidate **interview invitations** (not org membership — that lives under
`/api/v1/orgs/invitations/{token}`). Org identity comes from the `X-Org-Id`
header.

| Endpoint | Auth | Behavior | File:line |
| --- | --- | --- | --- |
| `POST ""` | org owner | Creates `CandidateInvitation`, emails `ACCEPT_URL` | `invitations.py:41` |
| `GET /{token}` | none | Verify invite (marks expired when past `expires_at`) | `invitations.py:102` |
| `POST /{token}/accept` | candidate | Creates `InterviewSession(session_type="invitation")` for the candidate | `invitations.py:131` |

### 8.7 System — mounted without prefix (`app/api/v1/system.py`)

`GET /api/v1/health` (`system.py:20`), `GET /api/v1/orgs/{org_id}/llm-status`
(owner), `GET /api/v1/orgs/{org_id}/llm-usage` (owner), and the email-template
editor: `GET /api/v1/orgs/{org_id}/email-templates`, plus
`GET`/`PUT /api/v1/orgs/{org_id}/email-templates/{name}` (owner,
`system.py:99,117`). Root: `GET /` (`main.py:154`) and `GET|POST /health`
(`main.py:159`).

### 8.8 Audit logs — `/api/v1/orgs/{org_id}/audit-logs` (`app/api/v1/audit_logs.py:15`)

`GET ""` — list org audit entries.

### 8.9 Intelligence — `/api/v1/intelligence/*` (`app/api/v1/intelligence.py`)

| Method + Path | Purpose | File:line |
| --- | --- | --- |
| `POST /intelligence/build` | One-shot V5 intelligence bundle; pass `session_id` to persist artifacts | `intelligence.py:47` |
| `GET /intelligence/brain/{session_id}` | `interview_brain`, `evidence_graph`, `timeline` snapshot | `intelligence.py:166` |

`POST /build` body — `IntelligenceBuildRequest` (`intelligence.py:34`):
`job_role`, `department_id?`, `candidate_id?`, `candidate_profile?`, `resume_text?`,
`required_competencies?`, `scorecard_competencies?`, `use_rag=true`, `use_llm=true`,
`session_id?`. Persists into `company_brains`, `interview_blueprints`, `scorecards`,
`candidate_brains`, `candidate_evidence_requirements` (best-effort).

### 8.10 Interview v4 shim (removed)

`app/api/interview_v4.py` existed only as a response-builder re-export after
the Phase 1 orchestration split. The Phase 8 dead-code pass stripped its
router, `process_v4_answer`, `_build_initial_state` and the dict write-back
helpers; the final Phase 10 cleanup deleted the module itself. All response
builders live in `app/engine/builders.py` and all write-back lives in
`app/engine/persistence.py`.

---

## 9. Engine architecture (V5)

### 9.1 `InterviewEngine` — `app/engine/engine.py`

A **thin coordinator** over the split engine modules (Phase 1). It speaks plain
dicts at the agent boundary and reconciles state through an `InterviewBrain`
(`app/core/interview_brain.py`) between turns.

| Module | Responsibility |
| --- | --- |
| `app/engine/lifecycle.py` | `start_session` — intelligence build + start node chain + first question |
| `app/engine/answer_processor.py` | `process_answer` — sanitize → evaluate → evidence → explainable score |
| `app/engine/routing.py` | `route_answer` — reflection → director → governor → question emit; `govern_difficulty` |
| `app/engine/decision.py` | `finalize_session` — synthesis → hiring decision → decision review → report |
| `app/engine/persistence.py` | best-effort DB writes (`persist_evidence`, `persist_answer_turn`, `persist_completion`, `persist_v5_snapshot`) |
| `app/engine/builders.py` | response frames (`build_start/answer/state/report_response`) |

Public API: `start_session(state, build_intelligence=False, **intelligence)`,
`process_answer(session_id, answer)`, `get_state(session_id)`,
`get_brain(session_id)`. `get_engine()` returns a singleton.

### 9.2 Response builders — `app/engine/builders.py`

| Builder | Frame | File:line |
| --- | --- | --- |
| `build_start_response` | `{type:"question"}` | `builders.py:36` |
| `build_answer_response` | `{type:"evaluation"}` | `builders.py:72` |
| `build_state_response` | `{type:"status_snapshot"}` | `builders.py:135` |
| `build_report_response` | `{type:"report"}` | `builders.py:166` |
| `compose_conversation_turn` | Spoken message = acknowledgement + bridge + question | `builders.py:22` |

### 9.3 Agent packages — `app/agents/`

| Package | Nodes (examples) |
| --- | --- |
| `init/` | `session_init_node`, `department_context_node`, `candidate_profile_node` |
| `planning/` | `competency_planner_node`, `strategy_brain_node`, `difficulty_governor`, `action_router` |
| `reasoning/` | `hypothesis_engine.hypothesis_node`, `reflection_engine.reflection_engine`, `evidence_engine.evidence_extractor_node` |
| `generation/` | `question_generator.question_generator_node` |
| `evaluation/` | `candidate_evaluator.unified_evaluator_node`, `scoring.explainable_scoring_node`, `synthesis.synthesis_node` |
| `decision/` | `director.director_controller`, `hiring_decision.hiring_decision_node`, `decision_review.decision_review_node` |

### 9.4 Explainable scoring — `app/agents/evaluation/scoring.py`

`reconcile_composite` computes the composite as a **weighted sum renormalized
over scored dimensions only**, returning `(composite, contributions)` sorted by
contribution. `explainable_scoring_node` replaces the raw LLM `evaluation_score`
and stores `score_reasons` (per-dimension rationale, low-confidence notes,
strongest-evidence, contradiction notes) on the brain. `_weights` merges custom
weights on top of `DEFAULT_DIMENSION_WEIGHTS`
(`technical .30 / reasoning .25 / communication .20 / confidence .10 /
behavioral .10 / completeness .05`).

### 9.5 Decision review — `app/agents/decision/decision_review.py`

The engine's "Evidence → Draft → Self Review → Final" stage. `review_decision`
runs four deterministic checks — insufficient evidence, missing competency,
overconfidence, contradictions — ranked high→medium→low; `finalize_decision`
demotes `hire`/`no_hire` → `undecided` (capping confidence ≤0.5) when a high
issue is found and subtracts confidence for contradictions/overconfidence. The
report carries `flag_review`, `demoted_to_undecided` and a `review` block via
`brain.decision_review`.

### 9.6 Director — `app/agents/decision/director.py`

Pure, deterministic controller deciding the next interview action
(`CONTINUE` / `PROBE` / `CHANGE_COMPETENCY` / `FINISH`) from reflection signals,
hypothesis confidence, loop counters and question budget. Guards against
reflection loops: a target probed `MAX_CONSECUTIVE_PROBES=3` turns without a
belief shift forces a rotation; a confirmed/testing belief at
`DEEP_PROBE_CONFIRMED_FLOOR=0.7` triggers a counter-evidence probe.

### 9.7 LLM tiering — `app/models/llm.py` + `app/services/llm_service.py`

`invoke` / `invoke_stream` / `invoke_structured` accept a `tier=` kwarg resolved
via `get_llm(tier)` (`cheap` / `strong` / `openrouter`). The **cheap** tier
(`llama-3.1-8b-instant` → local `one` → strong-chain fallback) is used for
evaluation, difficulty governing, question generation, resume analysis and
intelligence building; the **strong** tier (`llama-3.3-70b-versatile` → local →
`openrouter/auto-beta`) for synthesis and the hiring decision. The LLM cache key
includes the tier.

### 9.8 Reflection inputs — `app/agents/reasoning/contradiction_engine.py`

`reflection_engine` now supplies an evidence-count-weighted
`average_evidence_confidence`, `difficulty_reached`, `unanswered_hypotheses`
(untested/testing), `coverage_ratio`, `budget_remaining` and `contradiction_count`
(the `reflection_inputs` dict on the brain). Sufficiency verdicts are tempered by
evidence quality, and `decide_next_action` finishes early at
`difficulty_reached >= 3 and coverage >= 0.7 and question_number >= 5`.

### 9.9 Intelligence bundle — `app/intelligence/`

`build_interview_intelligence(job_role, department_id, style, candidate_profile,
candidate_id, resume_text, required_competencies, scorecard_competencies, …)`
(`app/intelligence/__init__.py:41`) produces the 6-key bundle
`InterviewEngine.start_session` accepts:

`company_brain`, `interview_blueprint`, `candidate_brain`,
`initial_hypotheses`, `evidence_requirements`, `candidate_assessment`.

Every stage is best-effort (RAG/LLM failures degrade to deterministic fallbacks).
`app/intelligence/company_cache.py` provides `get_or_build_company_brain`
used at WS boot.

### 9.10 State contract

- **`app/core/interview_state.py`** — `InterviewState` dict, plus
  `brain_to_dict`, `dict_to_brain`, `sync_brain` reconciliation helpers.
- **`app/core/interview_brain.py`** — `InterviewBrain` wrapper with
  `.to_dict()`, `.bump_version()`, and typed accessors for hypotheses,
  evidence, competency summary, director, score reasons, decision review, etc.
- **Store** — `app/services/v4_session_store.py` (`get_v4_session_store`):
  in-memory state + checkpoints, flushed on shutdown (`main.py:60-65`).

### 9.11 Styles

Only **AURA** is active. `get_style(name)` (`app/config/interview_styles.py:555`)
resolves `STANDARD` and any unknown name to AURA; old styles remain in `STYLES`
only for legacy route/test compatibility. Key AURA settings: persona `conductor`,
`difficulty_range (1,4)`, `max_questions 14`, `early_termination_threshold 0.85`,
evaluator weights `{technical .25, reasoning .25, behavioral .20, communication
.15, completeness .10, confidence .05}`.

---

## 10. Key data model

| Table | Model (db.py) | Purpose |
| --- | --- | --- |
| `organizations` | `Organization` `:82` | Tenant; hosts listings, departments, members. |
| `departments` | `Department` `:193` | Org sub-unit; owns templates, documents, sessions. |
| `interview_templates` | `InterviewTemplate` `:389` | Role/competency template; links `scorecard_template_id`. |
| `public_interviews` | `PublicInterview` `:570` | Public listing; `token`, `is_open`, time windows. |
| `public_interview_submissions` | `PublicInterviewSubmission` `:622` | Per-start submission record (email/name). |
| `interview_sessions` | `InterviewSession` `:250` | Anchor row; `status`, `final_score`, `engine_version`, `scorecard_template_id`. |
| `interview_messages` | `InterviewMessage` `:317` | Per-turn question/answer transcript. |
| `interview_evaluations` | `InterviewEvaluation` `:350` | Per-answer score, technical/communication, strengths/weaknesses. |
| `candidate_profiles` | `CandidateProfile` `:424` | Candidate account + profile_data + resume_url. |
| `candidate_sessions` | `CandidateSession` `:544` | Practice session link. |
| `scorecard_templates` | `ScorecardTemplate` `:990` | Org competency definitions. |
| `scorecard_results` | `ScorecardResult` `:1017` | Computed per session+template. |
| `evidence_store` | `EvidenceStore` `:796` | Per-competency evidence rows (engine output). |
| `company_brains` | `CompanyBrain` `:1047` | V5 company intelligence artifact. |
| `scorecards` | `Scorecard` `:1085` | V5 per-interview weighted scorecard. |
| `interview_brains` | `InterviewBrain` `:1245` | V5 brain snapshot. |
| `evidence_graphs` | `EvidenceGraph` `:1278` | V5 evidence graph snapshot. |
| `interview_timelines` | `InterviewTimeline` `:1307` | V5 timeline events. |
| `interview_slots` / `slot_availability` / `bookings` | `InterviewSlot` `:659`, `SlotAvailability` `:688`, `Booking` `:717` | Scheduling. |
| `audit_logs` | `AuditLog` `:758` | Audit trail (auth, marketplace, public starts, candidate verify). |
