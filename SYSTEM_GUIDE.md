# AI Interview Agent — Complete System Guide

> Last updated: 2026-11-06
> Scope: IT-only interview platform
> This document explains what every user can do, the full interview flow, and how APIs, prompts, backend functions, and database tables connect.

## 1. System Summary

The platform lets an organization:
- Create an IT-only hiring workspace
- Upload organization documents
- Define IT interview templates and scorecards
- Publish interviews in the Opportunity Hub
- Receive candidate applications with resumes
- Review fit scores
- Invite candidates
- Run an AI interview
- Record hired/rejected outcomes
- View analytics, ranking, and audit logs

Candidates can:
- Browse and search Opportunity Hub listings
- View organization profiles
- Save listings
- Apply with profile and resume
- Accept or decline interview invitations
- Take practice interviews
- View their interview history and competency scores
- Manage their profile and resume

## 2. User Roles and Capabilities

### 2.1 Public visitor

Can:
- View the landing page
- Browse organizations in the Opportunity Hub
- View organization profiles
- View open interview listings
- Apply to a listing with email, name, and a required PDF CV (guests), or with the profile CV when logged in
- Start a public interview by listing token

Cannot:
- Access organization dashboards
- Manage documents or templates
- See other candidates' applications

### 2.2 Candidate

Can:
- Register, log in, or use Google login
- Verify email
- Reset password
- View and update profile
- Upload a resume
- Browse listings and save favorites
- Apply to listings
- Accept or decline an invitation
- Start practice interviews
- View interview history and detail
- View stats and competency scores

Candidate-side notes:
- `GET /api/v1/marketplace/applications/me` lists a candidate's applications; the My Applications page shows them. Both require a verified email.

### 2.3 Organization owner

One organization has exactly one owner user.

Can:
- Register and log in
- Manage organization profile
- Upload organization knowledge documents
- Create IT interview templates
- Create scorecard templates
- Publish and manage Opportunity Hub listings
- View applications
- Set fit score and fit summary
- Invite a candidate
- Record a final outcome
- View analytics and candidate ranking
- View audit logs
- Export candidate ranking as CSV

Cannot:
- Add teammates
- Invite organization members
- Create departments
- Transfer organization ownership through the current UI

### 2.4 Admin

Admin is a platform-level flag on a user (`users.is_admin`).

Can:
- View platform stats
- View all organizations
- Suspend or activate an organization
- View all users
- View system health
- View LLM provider status and usage
- View and edit email templates

## 3. Scope Rules

- One organization has one owner user via `organizations.owner_user_id`.
- There is no `departments` table.
- One organization can publish many interviews through `public_interviews`.
- No `org_users`, `org_invitations`, or `candidate_sessions`.
- Every session references an IT role via `interview_sessions.it_role_id`.
- Organization documents belong to the organization.
- Competencies are IT-only (`competencies.scope = 'IT'`).
- Evaluation data is consolidated into `interview_intelligence`.

## 4. High-Level Architecture

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, React Router 6 |
| Backend | FastAPI, Python 3.12, async SQLAlchemy |
| Database | PostgreSQL / Supabase |
| Cache / session store | Redis with in-memory fallback |
| Vector store | Pinecone |
| LLM | OpenRouter primary, Groq fallback |
| Embeddings | sentence-transformers |
| Email | Resend |

Main backend areas:
- `app/api/` — HTTP and WebSocket routes
- `app/agents/` — question, evaluation, planning, reasoning, decision agents
- `app/engine/` — interview orchestration
- `app/intelligence/` — company, candidate, blueprint, role profiling
- `app/brain/` — brain assembly
- `app/rag/` — document ingestion and retrieval
- `app/marketplace/` — Opportunity Hub
- `app/candidates/` — candidate auth, profile, practice
- `app/orgs/` — organization ownership
- `prompts/` — all LLM prompts

## 5. End-to-End Organization Journey

### Step 1 — Organization registers

API:
- `POST /api/v1/auth/register`

Function:
- `app/auth/service.py::register`

What happens:
- User is created.
- Organization is created with `owner_user_id`.
- No department is created.
- Refresh token is issued.

Tables:
- `users`
- `organizations`
- `refresh_tokens`

### Step 2 — Owner logs in

API:
- `POST /api/v1/auth/login`

Function:
- `app/auth/service.py::login`

What happens:
- Password is verified.
- Organization is loaded by `owner_user_id`.
- Owner membership is returned.

Tables:
- `users`
- `organizations`
- `refresh_tokens`

### Step 3 — Upload organization documents

API:
- `POST /api/v1/departments/0/documents`

Function:
- `app/api/v1/departments.py::upload_document`

What happens:
- File type is checked.
- File is saved.
- `organization_documents` row is created.
- Background RAG processing extracts text, splits chunks, and stores embeddings in Pinecone.

Tables:
- `organization_documents`

Background function:
- `app/api/v1/departments.py::_process_document`
- `app/rag/loader.py::load_pdf`
- `app/rag/splitter.py::split_documents`
- `app/rag/pinecone_store.py::store_department_knowledge`

### Step 4 — Create an IT interview template

API:
- `POST /api/v1/departments/0/templates`

Function:
- `app/api/v1/departments.py::create_template`

What happens:
- Free-text role is resolved to an IT role.
- Template is stored with `org_id`, `it_role_id`, and `job_role_snapshot`.

Tables:
- `interview_templates`
- `it_roles`

Helper:
- `app/services/it_role_resolver.py::resolve_it_role`

### Step 5 — Create a scorecard template

API:
- `POST /api/v1/orgs/{org_id}/scorecards`

Function:
- `app/api/v1/scorecards.py`

Tables:
- `scorecard_templates`

### Step 6 — Publish an Opportunity Hub listing

API:
- `POST /api/v1/marketplace/interviews`

Function:
- `app/marketplace/service.py::create_public_interview`

What happens:
- Listing is stored with `org_id`, `it_role_id`, title, mode, token, and optional template.
- A rich description can be generated asynchronously.

Tables:
- `public_interviews`
- `interview_templates`
- `organizations`

Background prompt:
- `prompts/marketplace/job_description.md`

## 6. Candidate Opportunity Hub Journey

### Step 7 — Candidate browses listings

APIs:
- `GET /api/v1/marketplace/organizations`
- `GET /api/v1/marketplace/organizations/{slug}`
- `GET /api/v1/marketplace/interviews/{interview_id}`

Functions:
- `app/marketplace/service.py::list_organizations`
- `app/marketplace/service.py::get_org_profile`
- `app/marketplace/service.py::get_public_interview`

Tables:
- `organizations`
- `public_interviews`

### Step 8 — Candidate saves a listing

APIs:
- `POST /api/v1/candidates/saved-listings/{listing_id}`
- `DELETE /api/v1/candidates/saved-listings/{listing_id}`
- `GET /api/v1/candidates/saved-listings`

Tables:
- `candidate_saved_listings`

### Step 9 — Candidate applies

API:
- `POST /api/v1/marketplace/interviews/{interview_id}/apply`

Function:
- `app/marketplace/service.py::apply_to_public_interview`

What happens:
- The request is `multipart/form-data` (email, name, `resume` PDF; the bearer token identifies a logged-in candidate).
- Guests: a `candidate_profiles` row is found by email (case-insensitive) or created with `is_registered = false`. If the email belongs to a registered account the guest is told to sign in (409).
- A CV is required. Guests must upload one; logged-in candidates reuse the profile CV or upload one. Uploads go through `resume_service.store_candidate_resume` (PDF, 5 MB max): file saved under `resumes/`, text extracted, `candidate_documents` row created, `candidate_profiles.resume_url` updated.
- The application is linked to the CV through `resume_document_id`.
- Registering later with the same email claims the guest profile (same `candidate_profiles.id`); after email verification its applications, CV and sessions appear in the account.
- Application is created with:
  - `fit_status = pending`
  - `status = applied`
  - `org_decision = pending`
  - `candidate_response = pending`
  - `outcome = pending`

- After the response, two background tasks run: the "application received" email and the automatic fit evaluation.

Automatic fit evaluation (`app/marketplace/fit_evaluation.py`, prompt `evaluation/application_fit.md`):
- `fit_status`: `pending` -> `running` -> `completed` | `failed`. A failure never blocks the application; the owner can re-run it (`POST /applications/{id}/evaluate`).
- Inputs: the listing, the IT role's `role_competencies`, the organization's documents through org-scoped RAG (`get_org_retriever(org_id)`, namespace `department_{org_id}`), and the CV text.
- Output: `fit_score` (0-10), `fit_summary`, `fit_breakdown` (matched/missing competencies, strengths, risks, interview probes). On success `status` moves `applied` -> `evaluated`. Nobody is rejected automatically.
- Organization documents also feed the live interview: the WebSocket start passes `org_id` into the company brain and `department_context_node`. Uploading or deleting a document evicts that organization's cached company brains.

Tables:
- `candidate_profiles`
- `candidate_documents`
- `public_interviews`
- `public_interview_submissions`

### Step 10 — Organization reviews the application

APIs:
- `GET /api/v1/marketplace/org/{org_id}/applications`
- `POST /api/v1/marketplace/applications/{application_id}/fit`

Functions:
- `app/marketplace/service.py::list_org_applications`
- `app/marketplace/service.py::set_application_fit`

What happens:
- Owner sees application and resume.
- Owner stores `fit_score` and `fit_summary`.
- Status moves to `screening`.

Tables:
- `public_interview_submissions`
- `candidate_profiles`
- `candidate_documents`
- `organization_documents`
- `role_competencies`

### Step 11 — Organization invites candidate

API:
- `POST /api/v1/marketplace/applications/{application_id}/invite` (also emails the candidate a link to `/application-invite/{invite_token}`; email needs `RESEND_API_KEY`, otherwise it is logged as disabled)
- Guest path, no login: `GET/POST /api/v1/marketplace/application-invitations/{token}[/respond]`; accepting returns the `session_id` plus an `access_token`. The page stores the token (sessionStorage) and opens `/interview/{session_id}`; the interview WebSocket sends it as `?access=` and refuses any connection without it or the owner's login
- `POST /api/v1/marketplace/applications/{application_id}/invite`

Function:
- `app/marketplace/service.py::invite_application`

What happens:
- Interview session is created with:
  - `org_id`
  - `it_role_id`
  - candidate profile
  - `job_role_snapshot`
  - `invite_token`
  - `invite_expires_at`
- Application becomes:
  - `org_decision = invited`
  - `status = interview_offered`
  - `invited_at` set

Tables:
- `interview_sessions`
- `public_interview_submissions`

### Step 12 — Candidate accepts or declines

API:
- `POST /api/v1/marketplace/applications/{application_id}/respond`

Function:
- `app/marketplace/service.py::respond_to_application`

What happens:
- Candidate must own the application.
- Response must be `accepted` or `declined`.
- Accepted:
  - `candidate_response = accepted`
  - `status = interview_accepted`
- Declined:
  - `candidate_response = declined`
  - `status = interview_declined`
  - session becomes `cancelled`

Tables:
- `public_interview_submissions`
- `interview_sessions`

## 7. Full Interview Runtime Flow

### 7.1 Start the interview

Client connects:
- `WS /ws/interview/{session_id}?token=<candidate_token>`

Then sends:
```json
{"type": "start_interview"}
```

Backend:
- `app/api/interview_ws.py::interview_websocket`
- `app/api/interview_ws.py::_start_v4_engine`

Steps:
1. Load `interview_sessions`.
2. Load `organizations`.
3. Load candidate profile/resume.
4. Build role context:
   - `app/intelligence/role_competency_profiler.py::build_role_context`
5. Resolve competencies:
   - `app/data/competency_resolver.py::resolve_competencies`
6. Load or build company brain:
   - `app/intelligence/company_intelligence_builder.py::build_company_brain`
7. Build initial state:
   - job role
   - `org_id`
   - `it_role_id`
   - candidate profile
   - resume text
   - competency taxonomy
8. Start engine:
   - `app/engine/engine.py::InterviewEngine.start_session`
   - `app/engine/lifecycle.py::start_session`

### 7.2 Start-session node chain

In order:
1. `app/agents/init/session_init.py::session_init_node`
2. `app/agents/init/company_context.py::department_context_node`
3. `app/agents/init/candidate_profile.py::candidate_profile_node`
4. `app/agents/planning/competency_planner.py::competency_planner_node`
5. `app/agents/planning/strategy_planner.py::strategy_brain_node`
   - Prompt: `prompts/interview/strategy_brain.md`
6. `app/agents/reasoning/hypothesis_engine.py::hypothesis_node`
7. `app/agents/generation/question_generator.py::question_generator_node`
   - Prompt: `prompts/interview/question_generation.md`

Persistence:
- `app/intelligence/persist.py::persist_intelligence_bundle`
- `app/services/v5_brain_persister.py::V5BrainPersister.save_snapshot`

Tables:
- `interview_sessions`
- `interview_brain`
- `interview_intelligence`
- `interview_timeline`
- `evidence_store`
- `hypotheses`

### 7.3 Start response

The WebSocket returns:
```json
{
  "type": "question",
  "question": "...",
  "question_number": 1,
  "phase": "intro",
  "difficulty_level": 1
}
```

### 7.4 Candidate submits an answer

Client sends:
```json
{
  "type": "submit_answer",
  "candidate_answer": "...",
  "paste_chars": 0,
  "focus_lost_count": 0
}
```

Backend:
- `app/api/interview_ws.py::interview_websocket`
- `app/engine/engine.py::InterviewEngine.process_answer`
- `app/engine/answer_processor.py::process_answer`

Answer pipeline:
1. Sanitize input:
   - `app/utils/input_sanitizer.py::sanitize_user_input`
2. Detect prompt injection:
   - `app/utils/input_sanitizer.py::detect_prompt_injection`
3. Anti-cheat assessment:
   - `app/services/anti_cheat.py::assess`
4. Append Q/A to conversation history.
5. Evaluate answer:
   - `app/agents/evaluation/candidate_evaluator.py::unified_evaluator_node`
   - Prompt: `prompts/evaluation/unified_evaluator.md`
6. Extract evidence:
   - `app/agents/reasoning/evidence_engine.py::evidence_extractor_node`
7. Explainable scoring:
   - `app/agents/evaluation/scoring.py::explainable_scoring_node`
8. Persist evidence:
   - `app/engine/persistence.py::persist_evidence`
9. Route next step:
   - `app/engine/routing.py::route_answer`
   - `app/engine/routing.py::reflect_and_select`
   - `app/engine/routing.py::govern_difficulty`
   - `app/engine/routing.py::emit_question_and_persist`

Routing prompts/functions:
- Reflection:
  - `app/agents/reasoning/reflection_engine.py::reflection_engine`
- Brain layers:
  - `app/brain/assembler.py::refresh_brain_layers`
- Director:
  - `app/agents/decision/director.py::director_controller`
- Difficulty:
  - `app/agents/planning/difficulty_engine.py`
  - Prompt: `prompts/difficulty_governor/difficulty_governor.md`
- Question generation:
  - `app/agents/generation/question_generator.py::question_generator_node`
  - Prompt: `prompts/interview/question_generation.md`

Persistence after each turn:
- `app/engine/persistence.py::persist_answer_turn`
- `app/services/v5_brain_persister.py::V5BrainPersister.save_snapshot`
- `app/services/v5_brain_persister.py::V5BrainPersister.save_relational`

Tables:
- `interview_messages`
- `interview_evaluations`
- `evidence_store`
- `hypotheses`
- `interview_brain`
- `interview_intelligence`
- `interview_timeline`
- `scorecard_results`

### 7.5 Finalize interview

Trigger:
- Maximum questions reached, or decision says finish.

Function:
- `app/engine/decision.py::finalize_session`

Order:
1. Fold the last evidence into hypotheses.
2. Refresh sufficiency and recommendation:
   - `app/engine/builders.py::refresh_sufficiency_and_recommendation`
3. Synthesis:
   - `app/agents/evaluation/synthesis.py::synthesis_node`
   - Prompt: `prompts/evaluation/synthesis.md`
4. Evidence reading:
   - `app/agents/evaluation/evidence_reading.py::evidence_reading_node`
   - Prompt: `prompts/evaluation/evidence_reading.md`
5. Hiring decision:
   - `app/agents/decision/hiring_decision.py::hiring_decision_node`
   - Prompt: `prompts/decision/hiring_decision.md`
6. Decision review:
   - `app/agents/decision/decision_review.py::decision_review_node`
7. Assemble AURA brain:
   - `app/brain/assembler.py::build_aura_from_state`
8. Apply calibration verdict:
   - `app/engine/decision.py::apply_calibration_verdict`
9. Persist answer turn and completion.
10. Build report:
   - `app/engine/builders.py::build_report_response`
11. Persist final snapshot:
   - `app/services/v5_brain_persister.py::V5BrainPersister.save_snapshot`
   - `app/services/v5_brain_persister.py::V5BrainPersister.save_relational`

Tables:
- `interview_sessions`
- `interview_brain`
- `interview_intelligence`
- `interview_timeline`
- `hypotheses`
- `scorecard_results`
- `evidence_store`
- `audit_log` where applicable

### 7.6 Post-interview summary

API:
- `GET /api/v1/interviews/{session_id}/summary`

Function:
- `app/api/interview_agent.py::get_session_summary`

Tables:
- `interview_sessions`
- `interview_messages`
- `interview_evaluations`
- `interview_brain`

### 7.7 Final organization outcome

API:
- `POST /api/v1/marketplace/applications/{application_id}/outcome`

Function:
- `app/marketplace/service.py::set_application_outcome`

Values:
- `hired`
- `rejected`

Tables:
- `public_interview_submissions`

## 8. API Map

Full endpoint details are in [`CLAUDE_API_CATALOG.md`](CLAUDE_API_CATALOG.md).

Main groups:
- Auth: `/api/v1/auth/*`
- Organizations: `/api/v1/orgs/*`
- Admin: `/api/v1/admin/*`
- Analytics: `/api/v1/analytics/*`
- Audit: `/api/v1/orgs/{org_id}/audit-logs`
- Candidates: `/api/v1/candidates/*`
- Candidate ranking: `/api/v1/orgs/{org_id}/candidates/*`
- Demo: `/api/v1/demo/*`
- Organization documents/templates: `/api/v1/departments/*`
- Intelligence: `/api/v1/intelligence/*`
- Invitations: `/api/v1/invitations/*`
- Marketplace / Opportunity Hub: `/api/v1/marketplace/*`
- Public: `/api/v1/public/*`
- Scorecards: `/api/v1/orgs/{org_id}/scorecards/*`
- System: `/api/v1/health`, `/api/v1/orgs/{org_id}/llm-*`, `/api/v1/orgs/{org_id}/email-templates/*`
- Interview summary: `/api/v1/interviews/{session_id}/summary`
- Interview WebSocket: `/ws/interview/{session_id}`

## 9. Prompt Map

Full prompt details are in [`CLAUDE_PROMPT_CATALOG.md`](CLAUDE_PROMPT_CATALOG.md).

| Stage | Prompt |
|---|---|
| Strategy | `prompts/interview/strategy_brain.md` |
| Question generation | `prompts/interview/question_generation.md` |
| Answer evaluation | `prompts/evaluation/unified_evaluator.md` |
| Evidence reading | `prompts/evaluation/evidence_reading.md` |
| Final synthesis | `prompts/evaluation/synthesis.md` |
| Difficulty | `prompts/difficulty_governor/difficulty_governor.md` |
| Hiring decision | `prompts/decision/hiring_decision.md` |
| Company intelligence | `prompts/intelligence/company_brain.md` |
| Blueprint | `prompts/intelligence/interview_blueprint.md` |
| Resume analysis | `prompts/intelligence/resume_analysis.md` |
| Role profiling | `prompts/intelligence/role_competency_profiler.md` |
| Marketplace description | `prompts/marketplace/job_description.md` |

Prompt loader:
- `app/services/prompt_loader.py::load_prompt`
- `app/services/prompt_loader.py::PromptLoader.load_by_path`

## 10. Function Map

| Area | Key functions |
|---|---|
| Auth | `register`, `login`, `google_login`, `refresh`, `logout` |
| Org ownership | `create_org`, `get_org`, `update_org`, `list_members` |
| Documents | `upload_document`, `_process_document`, `delete_document` |
| Templates | `create_template`, `list_templates`, `update_template`, `delete_template` |
| Marketplace | `create_public_interview`, `list_organizations`, `get_public_interview` |
| Applications | `apply_to_public_interview`, `set_application_fit`, `invite_application`, `respond_to_application`, `set_application_outcome` |
| Candidate | `register`, `login`, `start_practice`, `get_interviews`, `get_competency_scores` |
| Interview engine | `start_session`, `process_answer`, `route_answer`, `finalize_session` |
| Start chain | `session_init_node`, `department_context_node`, `candidate_profile_node`, `competency_planner_node`, `strategy_brain_node`, `hypothesis_node`, `question_generator_node` |
| Answer pipeline | `unified_evaluator_node`, `evidence_extractor_node`, `explainable_scoring_node`, `persist_evidence` |
| Routing | `reflect_and_select`, `govern_difficulty`, `emit_question_and_persist` |
| Finalize | `synthesis_node`, `evidence_reading_node`, `hiring_decision_node`, `decision_review_node`, `apply_calibration_verdict` |
| Persistence | `persist_intelligence_bundle`, `V5BrainPersister.save_snapshot`, `V5BrainPersister.save_relational` |

## 11. Data Map by Stage

| Stage | Tables |
|---|---|
| Register/login | `users`, `organizations`, `refresh_tokens`, `user_password_reset_tokens` |
| Documents | `organization_documents` |
| Templates | `interview_templates`, `scorecard_templates`, `it_roles`, `competencies`, `role_competencies` |
| Listings | `public_interviews` |
| Applications | `public_interview_submissions`, `candidate_profiles`, `candidate_documents` |
| Interview start | `interview_sessions`, `interview_brain`, `interview_intelligence`, `interview_timeline` |
| Answer turns | `interview_messages`, `interview_evaluations`, `evidence_store`, `hypotheses` |
| Finalize | `scorecard_results`, `interview_brain`, `interview_intelligence` |
| Post-interview | `interview_sessions`, `interview_messages`, `interview_evaluations`, `interview_brain` |
| Outcome | `public_interview_submissions` |
| Analytics | `interview_sessions`, `interview_evaluations`, `interview_brain`, `it_roles` |
| Audit | `audit_log` |

## 12. What Works Now

- Auth/org owner flow
- Organization documents upload
- Organization templates
- Marketplace listings
- Opportunity Hub apply / fit / invite / respond / outcome
- Candidate practice session creation
- Interview start and answer pipeline (runtime)
- Consolidated intelligence persistence
- Analytics/ranking mapped to IT roles
- IT catalog seeded with 179 roles and 60 competencies
- Supabase updated to 30 tables

## 13. What Is Not Finished

- Frontend still uses old department/member screens.
- IT-only prompt wording is not fully audited.
- Organization direct interview start endpoint is not mounted; current creation paths are marketplace, invitation, and practice.
- Candidate application list/status UI is missing.
- Scheduling and calibration code exists but is not mounted.
- Legacy models and endpoints still need cleanup.
- Full legacy test suite is not updated.

## 14. Runbook

```powershell
venv\Scripts\python.exe -m alembic upgrade head
venv\Scripts\python.exe scripts\seed_it_catalog.py
venv\Scripts\python.exe -m pytest tests\test_it_catalog.py -q
venv\Scripts\python.exe -c "import app.main; print('app imports')"
```

## 15. Glossary

| Term | Meaning |
|---|---|
| Opportunity Hub (OH) | Public marketplace of organizations and interview listings |
| IT role | A role from the `it_roles` catalog |
| Competency | An IT capability used for scoring |
| Role competency | Weighted competency requirement for an IT role |
| Application | Candidate submission for a public interview |
| Fit score | Organization's assessment of candidate match |
| Interview session | One interview attempt |
| Brain | Persisted AI reasoning state |
| `interview_intelligence` | Consolidated JSONB intelligence row per session |
| Calibration | Final verdict override based on difficulty and evidence sufficiency |
| RAG | Retrieval-Augmented Generation over organization documents |

## 16. Reference Documents

- [`CLAUDE_HANDOFF.md`](CLAUDE_HANDOFF.md)
- [`CLAUDE_API_CATALOG.md`](CLAUDE_API_CATALOG.md)
- [`CLAUDE_PROMPT_CATALOG.md`](CLAUDE_PROMPT_CATALOG.md)
- [`docs/it-scope/README.md`](docs/it-scope/README.md)
- [`docs/it-scope/01-scope-change.md`](docs/it-scope/01-scope-change.md)
- [`docs/it-scope/02-glossary.md`](docs/it-scope/02-glossary.md)
- [`docs/it-scope/04-final-table-list.md`](docs/it-scope/04-final-table-list.md)
- [`docs/it-scope/05-erd-student-level.md`](docs/it-scope/05-erd-student-level.md)
- [`docs/it-scope/schema.sql`](docs/it-scope/schema.sql)
