# CLAUDE HANDOFF — AI Interview Agent

> Last updated: 2026-11-06
> Repository: `D:\projectiqram\AI\AI-Interview-Agent`
> Status: backend largely aligned; Opportunity Hub application UI/API exists; candidate CV-required application flow, automatic fit evaluation, email invites, and account claiming remain.

## 0. Current Priority — Candidate Application Flow

The next product work is defined in [`CLAUDE_APPLICATION_FLOW_HANDOFF.md`](CLAUDE_APPLICATION_FLOW_HANDOFF.md).

Locked decisions:
1. Guests apply with email, name, and a required CV.
2. Logged-in candidates use their profile CV or upload one during apply.
3. Applications are evaluated automatically against organization documents, IT role, role competencies, and CV.
4. Organizations review fit scores and invite candidates by email.
5. Guests can accept an invite and interview without an account.
6. Registering with the same email claims the guest profile and history after verification.

Read the application handoff before changing application, resume, invite, email, or RAG code.

For the exact copy-paste instruction to send to the next Claude terminal, use [`CLAUDE_TERMINAL_PROMPT.md`](CLAUDE_TERMINAL_PROMPT.md).

## 1. What This System Is

An AI interview platform restricted to the **IT field only**.

It supports:
- Organization owner accounts
- IT role catalog
- IT competencies
- Organization knowledge documents
- Interview templates and scorecards
- Opportunity Hub interview listings
- Candidate applications with resumes
- Organization fit review / invite / final outcome
- AI interview runtime
- Evidence, hypotheses, brain snapshots, and scorecards
- Candidate practice sessions
- Analytics, ranking, audit logs, and admin views

## 2. Scope Rules

These are hard rules. Do not undo them.

1. One organization has exactly **one owner user** via `organizations.owner_user_id`.
2. There is **no `departments` table**.
3. One organization can publish many interviews through `public_interviews`.
4. There is **no `org_users`**, **no `org_invitations`**, and **no `candidate_sessions`**.
5. Every interview session references an IT role through `interview_sessions.it_role_id`.
6. Documents belong to the organization through `organization_documents.org_id`.
7. Competencies are IT-only (`competencies.scope = 'IT'`).
8. Evaluation/intelligence data is consolidated into `interview_intelligence`.
9. Preserve users, organizations, organization documents, candidate profiles, and resumes during migrations.

## 3. Source of Truth

Read these first:

- [`docs/it-scope/README.md`](docs/it-scope/README.md)
- [`docs/it-scope/01-scope-change.md`](docs/it-scope/01-scope-change.md)
- [`docs/it-scope/02-glossary.md`](docs/it-scope/02-glossary.md)
- [`docs/it-scope/04-final-table-list.md`](docs/it-scope/04-final-table-list.md)
- [`docs/it-scope/05-erd-student-level.md`](docs/it-scope/05-erd-student-level.md)
- [`docs/it-scope/schema.sql`](docs/it-scope/schema.sql)
- [`docs/it-scope/seed-it-catalog.sql`](docs/it-scope/seed-it-catalog.sql)
- [`SYSTEM_GUIDE.md`](SYSTEM_GUIDE.md)
- [`CLAUDE_API_CATALOG.md`](CLAUDE_API_CATALOG.md)
- [`CLAUDE_PROMPT_CATALOG.md`](CLAUDE_PROMPT_CATALOG.md)
- [`CLAUDE_APPLICATION_FLOW_HANDOFF.md`](CLAUDE_APPLICATION_FLOW_HANDOFF.md)
- [`CLAUDE_TERMINAL_PROMPT.md`](CLAUDE_TERMINAL_PROMPT.md) — ready-to-paste implementation prompt

Reference only:
- `docs/archive/legacy-aura/`

Superseded:
- `docs/it-scope/03-database-schema.md` (older 25-table lean reference)

## 4. Architecture

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, React Router 6 |
| Backend | FastAPI, Python 3.12, async SQLAlchemy |
| Database | PostgreSQL / Supabase |
| Cache / session store | Redis with in-memory fallback |
| Vector store | Pinecone |
| LLM providers | OpenRouter primary, Groq fallback |
| Embeddings | sentence-transformers |
| Email | Resend |
| Runtime graphs | LangGraph-style question/evaluation workflows |

### Important backend folders

| Folder | Responsibility |
|---|---|
| `app/api/` | HTTP and WebSocket endpoints |
| `app/api/v1/` | Versioned REST routes |
| `app/agents/` | Interview agents: generation, evaluation, planning, reasoning, decision |
| `app/engine/` | Interview engine, lifecycle, decision, persistence |
| `app/brain/` | Company, role, candidate, and interview brain assembly |
| `app/core/` | `InterviewBrain` state object |
| `app/intelligence/` | Company/candidate intelligence, blueprint, role profiler, scorecard resolver |
| `app/rag/` | Pinecone document ingestion and retrieval |
| `app/services/` | Auth helpers, persistence, prompt loader, email, cache, marketplace generator |
| `app/models/` | SQLAlchemy ORM models |
| `app/repositories/` | Session/message/evaluation repositories |
| `app/marketplace/` | Opportunity Hub services and schemas |
| `app/candidates/` | Candidate auth, practice, resumes, history |
| `app/orgs/` | Organization CRUD and owner lookups |
| `app/scheduling/` | Legacy scheduling code; not mounted |
| `prompts/` | All LLM prompt templates |

## 5. Backend Features

### 5.1 Auth and organization

- Organization owner registration
- Login, Google login, refresh, logout
- `/auth/me` returns owner membership
- Password reset tokens
- Single-owner organization model
- Admin role flag on users

### 5.2 IT catalog

- 179 IT roles across 23 families
- 60 IT competencies
- Role-to-competency mappings
- Role resolver maps free-text role to catalog slug
- Seed data in `docs/it-scope/seed-it-catalog.sql`

### 5.3 Organization documents

- Upload PDF/DOCX/TXT/MD
- Stored in `organization_documents`
- RAG namespace keyed by organization
- Pinecone ingestion and deletion
- Synthetic IT department compatibility via `/departments`

### 5.4 Templates and scorecards

- `interview_templates` keyed by `org_id` + `it_role_id`
- `scorecard_templates`
- Scorecard result calculation
- Template CRUD through `/departments/{id}/templates` and `/orgs/{org_id}/templates`

### 5.5 Opportunity Hub / marketplace

- Public organization directory
- Public interview listings
- Organization listing CRUD
- Candidate saved listings
- Candidate applications
- Fit score / fit summary
- Organization invite
- Candidate accept / decline
- Final outcome: hired / rejected
- Public token-based interview start

### 5.6 Candidates

- Candidate registration / login / Google login
- Candidate refresh tokens
- Email verification
- Password reset
- Profile update
- Resume upload
- Interview history and detail
- Stats and competency scores
- Practice sessions
- Saved listings

### 5.7 Interview runtime

- V5 `InterviewBrain` state
- Question generation
- Adaptive difficulty
- Evidence extraction
- Hypothesis tracking
- Consistency checks
- Observations
- Reflection and decision
- Hiring recommendation
- Brain snapshots
- Timeline events
- Scorecard results

### 5.8 Intelligence

- Company intelligence from organization documents
- Candidate intelligence from profile/resume
- Interview blueprint
- Role competency profiler
- Evidence requirements
- Consolidated persistence into `interview_intelligence`

### 5.9 Analytics and audit

- Organization overview
- Score trend and distribution
- Sessions by IT role
- Candidate ranking
- CSV export
- Audit logs
- Admin platform stats
- Admin organization and user views

### 5.10 Demo and tooling

- Local demo DB refresh endpoint
- IT catalog seed script
- Student-level ERD guide

### 5.11 Not currently mounted

These code files exist but their routers are not included in `app/main.py`:

- `app/api/v1/scheduling.py`
- `app/scheduling/service.py`
- `app/api/v1/calibration.py`

They reference removed tables. Treat them as legacy and delete or rewrite later.

## 6. Database

Supabase is updated.

- Application tables: **30**
- Plus `alembic_version`
- Direct connection is configured in `.env`
- The old pooler connection failed with:
  `FATAL: (ENOTFOUND) tenant/user postgres.rrvypykvbhxskokxdbrd not found`

Applied migrations:
- `d2e3f4a5b6c7` — final 30-table reset
- `e3f4a5b6c7d8` — one owner per organization
- `f4a5b6c7d8e9` — allow practice sessions without `org_id`

Preserved data:
- users: 7
- organizations: 2
- organization_documents: 8
- candidate_profiles: 10
- candidate_documents: 6
- audit_log: 21

Backup schema:
- `backup_it_reset`

## 7. Current Working Flows

### 7.1 Organization owner flow

1. Register owner user and organization.
2. `organizations.owner_user_id` points to the user.
3. Login returns the owner membership.
4. No department or teammate membership is created.

### 7.2 Organization documents flow

1. Upload a document through the department compatibility API.
2. Row is created in `organization_documents`.
3. Background RAG processing stores chunks in Pinecone.
4. Organization documents can be listed and deleted.

### 7.3 Opportunity Hub flow

1. Candidate sees open `public_interviews`.
2. Candidate applies with profile and resume.
3. Organization sees applications.
4. Organization records fit score and summary.
5. Organization invites; an `interview_sessions` row is created with `invite_token`.
6. Candidate accepts or declines.
7. Interview runs.
8. Organization records final outcome: `hired` or `rejected`.

Status values:
- Application: `applied`, `screening`, `interview_offered`, `interview_accepted`, `interview_declined`, `interviewed`, `hired`, `rejected`, `withdrawn`
- Org decision: `pending`, `invited`, `rejected`
- Candidate response: `pending`, `accepted`, `declined`
- Outcome: `pending`, `hired`, `rejected`

### 7.4 Interview runtime persistence

On each turn:
- `interview_brain` is upserted
- `interview_intelligence` is upserted
- `interview_timeline` gets a brain snapshot
- `hypotheses` are upserted
- `scorecard_results` is written at finalize

Removed tables are no longer written.

## 8. Verified

- Python files compile
- `app.main` imports
- Auth register/login against Supabase
- IT role resolver
- Opportunity Hub apply/fit/invite/respond/outcome
- Consolidated intelligence persistence
- Model queries against Supabase
- Test data cleaned up

Not verified:
- Full frontend flow
- Full legacy test suite
- Full IT-only taxonomy/prompt behavior
- Avatar/speech runtime (no mounted backend avatar WebSocket found)

## 9. Known Gaps

### Priority 0 - Candidate application flow

See [`CLAUDE_APPLICATION_FLOW_HANDOFF.md`](CLAUDE_APPLICATION_FLOW_HANDOFF.md).

Not done:
- CV-required application intake for guests and logged-in candidates.
- Guest CV storage and `resume_document_id` linking.
- Claim-on-register for guest candidate profiles.
- Automatic application fit evaluation through organization documents.
- Invite email delivery and public guest invite acceptance.
- Candidate application history verification gating.

### Priority 1 — Frontend

Completed:
- Remove department creation UI.
- Remove organization member/invite UI.
- Add IT role picker backed by `it_roles`.
- Update marketplace types from `department_id` to `it_role_id`.
- Add OH application screens:
  - apply
  - fit review
  - invite
  - candidate accept/decline
  - outcome

Remaining:
- Rename remaining department compatibility UI/routes where practical.
- Improve organization document UI naming.
- Extend candidate application UI with CV, fit details, and guest invite flow.
- Fix interview continuation to use WebSocket instead of removed REST question routes.
- Replace `department_id` practice detection with `session_type`/`org_id`.

### Priority 2 — IT-only prompts and taxonomy

- Ensure only IT competencies are resolved.
- Remove non-IT prompt branches.
- Rewrite prompt language that assumes departments.
- Validate role names against `it_roles`.

### Priority 3 — Legacy cleanup

- Delete or archive unmounted scheduling/calibration code.
- Delete legacy ORM models for removed tables.
- Remove old persistence methods that reference removed tables.
- Remove or return 410 on legacy organization member endpoints.

### Priority 4 — Tests

- Add tests for OH application flow.
- Add tests for organization document upload.
- Add tests for intelligence consolidation.
- Add tests for one-owner auth.
- Update old tests that still assume departments/org members.

## 10. Runbook

```powershell
# Apply migrations
venv\Scripts\python.exe -m alembic upgrade head

# Seed IT catalog
venv\Scripts\python.exe scripts\seed_it_catalog.py

# Targeted catalog test
venv\Scripts\python.exe -m pytest tests\test_it_catalog.py -q

# Import check
venv\Scripts\python.exe -c "import app.main; print('app imports')"
```

Do not run the full legacy test suite until it is updated. It is large and still assumes the old schema.

## 11. Guardrails

- Do not reintroduce departments, org_users, org_invitations, or candidate_sessions.
- Do not write to removed evaluation tables. Use `interview_intelligence`.
- Keep one owner per organization.
- Keep `public_interviews` as the multiple-interviews mechanism.
- Preserve user/org/document/resume data during migrations.
- Back up before destructive migrations.
- Expand acronyms before using them; maintain the glossary.
- Treat `docs/archive/legacy-aura/` as historical only.
- Check `CLAUDE_API_CATALOG.md` before changing endpoints.
- Check `CLAUDE_PROMPT_CATALOG.md` before changing prompts.

## 12. Suggested First Message to Claude

> Read `CLAUDE_HANDOFF.md`, `CLAUDE_API_CATALOG.md`, and `CLAUDE_PROMPT_CATALOG.md`. Then read `docs/it-scope/README.md`, `01-scope-change.md`, `02-glossary.md`, `04-final-table-list.md`, and `schema.sql`. The database is already updated in Supabase. Continue with the frontend alignment and IT-only taxonomy/prompt work. Do not reintroduce departments or removed tables.
