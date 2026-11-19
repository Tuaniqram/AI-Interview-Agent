# Session changes

Single-owner organizations, department removal, UI standardization, and supporting fixes.

## 1. Frontend shell and admin tables

- Removed the duplicate logo from `TopBar`; the sidebar now owns the brand mark.
- `TopBar` has a bottom border and aligns with the sidebar header height.
- Sidebar uses a solid `bg-section` surface with a right border instead of the washed-out `.glass` utility, so the navigation and content have a clear edge.
- `Card` uses a solid `bg-section` surface with a border instead of `.glass`.
- Admin Organizations page is a proper table with columns: Organization, Owner, Interviews, Status, Actions.
- Admin Users page is a proper table with columns: Name, Email, Organization, Role, Status, Joined. Non-admin accounts are labeled **Owner** (not Member).
- Email Templates page is centered with template chips, a large editor, an Edit/Preview toggle, and an unsaved-changes indicator.

## 2. Candidate feedback in plain language

- Added `app/services/feedback_text.py`:
  - `plain_feedback()` writes candidate-facing sentences without enum values or confidence ratios.
  - `legacy_to_plain()` rewrites older machine-readable feedback on read.
- `app/engine/persistence.py` now uses `plain_feedback()` when completing a session.
- `app/candidates/service.py` applies `legacy_to_plain()` to stored feedback, so existing records are readable without a migration.
- Tests: added `tests/test_feedback_text.py`; updated `tests/test_v4_writeback.py`.

## 3. Auth, CORS, and the admin panel

- CORS now accepts any loopback origin (`localhost` / `127.0.0.1`, any port) in dev, so Vite on `127.0.0.1` or a fallback port can call the API.
- Reset the seeded `admin@test.com` password to `Admin123!` in the configured database.
- Admin-only pages moved from the organization shell to the Admin panel:
  - Emails, Audit Logs, LLM, Health.
  - Routes live under `/admin/...`.
- `AdminShell` redirects non-admin users and includes the four new pages.
- Added platform-wide endpoints in `app/api/v1/admin.py`:
  - `GET /admin/audit-logs`
  - `GET /admin/llm-status`
  - `GET /admin/llm-usage`
  - `GET /admin/email-templates`
  - `GET/PUT /admin/email-templates/{name}`
- Audit, LLM, and email endpoints require `is_admin`.
- `app/api/v1/system.py` now only exposes health and the shared LLM provider helper.

## 4. Single-owner organizations (membership removal)

- Added `scripts/sanitize_single_user_orgs.py`:
  - Drops legacy `org_users` / `org_invitations` tables if present.
  - Deletes non-admin accounts that own no organization and are not candidates.
  - Verifies every organization has exactly one active owner.
  - Supports `--dry-run`.
- Ran the sanitizer: removed the four orphan member/viewer accounts; the database now has three users (admin + two owners).
- Removed member management code:
  - Member/invite endpoints and service stubs.
  - Member/invite request and response schemas (except the read-only owner response).
  - Frontend member state (`members`, `refreshMembers`), `listMembers`, and `OrgMember` types.
- `OrgRole` is now `owner` only.
- `GET /orgs/{org_id}/members` returns exactly the owner.
- Admin organization rows now expose `owner_name` / `owner_email` instead of `member_count`.

## 5. Department removal and organization-scoped content

- Deleted `app/api/v1/departments.py` and `app/schemas/department.py`.
- Added `app/api/v1/org_content.py` with organization-scoped endpoints:
  - `GET /orgs/{org_id}/sessions`
  - `GET /orgs/{org_id}/documents`
  - `POST /orgs/{org_id}/documents`
  - `DELETE /orgs/{org_id}/documents/{doc_id}`
  - `GET/POST /orgs/{org_id}/templates`
  - `GET/PUT/DELETE /orgs/{org_id}/templates/{template_id}`
- Removed the duplicate templates route from `app/api/v1/orgs.py`.
- `/api/v1/departments` is now gone (404).
- Frontend:
  - New **Company** page at `/org/company` (formerly the department detail page).
  - Removed `/departments` and `/departments/:id` routes.
  - Deleted `DepartmentList`, `DepartmentDetail`, `DepartmentCard`, and `departmentService`.
  - Moved document/history components to `components/org/`.
  - Added `orgContentService`.
  - Sessions page fetches the active organization directly; removed the Department column.
- Data naming standardized:
  - Analytics `/sessions/by-department` became `/sessions/by-it-role`.
  - `total_departments` became `total_it_roles`.
  - Candidate, marketplace, and invitation responses use `org_name`.
  - Candidate ranking uses `role_name` / `it_role_id`.

## 6. Interview mode removal

- The listing form no longer has an Interview Mode selector; new listings use `typing`.
- Removed the Opportunity Hub interview-mode filter and URL handling.
- Existing mode icons remain for display.

## 7. Email templates

- The admin editor now points at `app/emails/templates/`, the folder actually used by `app/services/email.py`.
- Previously it edited `app/templates/email/`, so admin edits had no effect on sent mail.
- Restyled all nine sent templates to the green system theme with:
  - Logo and wordmark header.
  - Green accent bar and primary button.
  - Information panels.
  - Footer with reason-for-email and copyright.
- Preview supports both `${VAR}` and `{{var}}`, filling sample values so the rendered email looks real.
- Saving preserves the original file extension.
- Deleted the unused `app/templates/email/` set.

## 8. Seed scripts

- `scripts/seed_v2.py` rewritten for the current schema:
  - System admin.
  - Two organizations, each with one owner.
  - One candidate profile.
  - Optional templates/invitations when the IT catalog exists.
  - No departments, members, or viewers.
- `scripts/reset_and_seed.py` now truncates the current public tables dynamically, preserving `it_roles`, `competencies`, `role_competencies`, and `alembic_version`.
- `scripts/verify_seed.py` rewritten to report users, admins, organizations, owners, orphan accounts, documents, templates, roles, candidates, and invitations.
- `scripts/seed_department_docs.py` renamed to `scripts/seed_org_documents.py`; uploads now target `/api/v1/orgs/{org_id}/documents`.
- `scripts/index_department_docs.py` replaced by `scripts/index_org_documents.py`, which indexes organization documents into the organization's Pinecone namespace.
- `scripts/generate_demo_assets.py`, `scripts/demo_autopilot.py`, and `scripts/reset_db.py` updated for org-scoped content.
- Added `scripts/prepare_demo.py`, which keeps one organization and one verified candidate, removes old sessions/listings/applications/templates/scorecards/CVs, and keeps the organization documents.
- Removed the obsolete `scripts/test_rbac.py`.
- Added `!changes.md` to `.gitignore` so this file is tracked instead of ignored by the `*.md` rule.

## 9. Interview report context

- `/interviews/{id}/summary` now includes `candidate_name`, `candidate_email`, and `org_name`.
- `/interviews/{id}/summary` also includes the persisted `scorecard` result.
- The report header shows the candidate, organization, and job role; the candidate email is available on hover.
- The report renders a Scorecard section: template name, weighted score, and per-competency scores.
- Removed the stale `department_id` from the `InterviewReport` type.
- Removed the unused `SessionRepository.get_session_summary`, which still read the dropped `department_id` column.
- Guarded the overall score against a missing value.

## 10. Scorecard and template wiring

- New migration `alembic/versions/c1a2b3c4d5e6_allow_saturated_and_summary.py`:
  - Allows the hypothesis status `saturated` in `hypotheses_status_check`.
  - Allows the `summary` phase in `interview_sessions_current_phase_check`.
  - Adds `interview_sessions.template_id` with a `SET NULL` FK to `interview_templates`.
- `InterviewSession.template_id` added to the model.
- `resolve_competencies()` accepts `template_id`; the linked listing template is preferred over the newest organization template.
- `start_public_interview()` stores `template_id` and passes it into competency resolution.
- `invite_application()` now:
  - Copies the listing template's `scorecard_template_id` into the session.
  - Stores `template_id`.
  - Sets `engine_version="v5"`.
  - Repairs these fields when re-sending an invite.
- `_start_v4_engine()` passes the session's `template_id` into competency resolution.
- `scorecards/service.py`:
  - `calculate_scorecard_for_session()` accepts `commit=False` for use inside the finalize transaction.
  - Stores competency names in the result.
  - Keeps one result per session and updates its template id.
- `v5_brain_persister.py`:
  - Normalizes hypothesis statuses before writing them.
  - Writes hypotheses, intelligence, and the scorecard under independent savepoints, so one bad row cannot lose the others.
  - On finalize, calculates the linked custom scorecard from evidence; otherwise writes AURA's built-in competency summary.
  - The built-in scorecard now records `average_score` and `average_confidence` correctly.
- `persist_completion()` isolates the `summary` phase update from the completion write.
- The report summary endpoint returns the scorecard, and the report page displays it.

## 11. End-to-end demo pipeline

- `scripts/prepare_demo.py` resets the demo: Nova AI, one owner (`nova@test.com`), one verified candidate (`candidate@test.com`), 7 organization documents, no old sessions/listings/applications/templates/scorecards/CVs.
- `tools/demo_interview.py` runs the real pipeline:
  1. Creates the `Senior Backend Scorecard` from the role's catalog competencies.
  2. Creates the `Senior Backend Interview Template` linked to that scorecard.
  3. Publishes the listing with the template.
  4. Candidate logs in, generates a PDF CV, and applies with it.
  5. Waits for the CV fit evaluation.
  6. Organization invites the candidate.
  7. Candidate accepts the invitation.
  8. The real WebSocket engine runs the interview and the candidate answers every question.
  9. Fetches the summary with a fresh organization token and writes `run.json` plus `frontend/public/demo-interview.html`.
- Demo page: `http://localhost:3000/demo-interview.html`.

## 12. Integration and regression tests

- Added `tests/integration/test_scorecard_pipeline.py` (opt-in, DB-backed):
  - Creates a temporary organization, user, role, scorecard, template, session, and evidence rows.
  - Writes a `saturated` hypothesis and a custom scorecard through `V5BrainPersister.save_relational(..., finalize=True)`.
  - Asserts the `saturated` hypothesis persists, the `summary` phase is accepted, and the `scorecard_results` row uses the linked template and includes competency names.
  - Deletes all temporary rows afterwards.
- Added to `tests/test_v5_persistence.py`:
  - `_normalize_hypothesis_status` keeps `saturated` and coerces unknown values to `testing`.
  - `_insert_scorecard_result` prefers the linked scorecard and calls the calculator with `commit=False`.
- `tests/integration/conftest.py` falls back to `settings.DATABASE_URL` when the environment variable is absent, so the integration suite uses `.env` with `PYTEST_USE_DB=1`.

## 13. Engine naming and reproducibility

- Renamed `_start_v4_engine` to `_start_engine` in `app/api/interview_ws.py`; updated the hardening test.
- Public and practice sessions now record `engine_version="v5"` and `flow_type="v5_evidence_driven"`.
- `.gitignore` now ignores `scripts/*` and unignores the seed/demo/sanitizer scripts, so a fresh checkout can run the demo setup.
- Updated `tests/test_marketplace_start.py` to expect the v5 flow type.

## 14. Scorecard results on the organization page

- Added `GET /api/v1/orgs/{org_id}/scorecards/results` in `app/api/v1/scorecards.py`.
  - Declared before `GET /{template_id}` so FastAPI does not parse `results` as a UUID.
  - Joins `scorecard_results` to `interview_sessions`, `candidate_profiles`, and `scorecard_templates`.
  - Organization-scoped, newest first, capped at 100 rows.
  - Returns session id, template name, candidate name/email, job role, session status, weighted score, and creation time.
- Added `ScorecardResultListItem` to `app/scorecards/schemas.py`.
- Added `scorecardService.listResults(orgId)` and the matching frontend type.
- The organization **Scorecards** page now shows a **Recent results** table:
  - Candidate, role, scorecard, weighted score (/10), and a **Report** link to `/interview/{session_id}/report`.
  - Empty state when no candidate has been scored yet.
  - A results fetch failure leaves the template list usable instead of failing the page.
- Long interviews:
  - The WebSocket interview access token is valid for 12 hours (`app/auth/interview_access.py`), so a 15+ minute interview does not lose its session credential.
  - The frontend `apiClient` refreshes the short-lived organization token on a 401 and retries the request, including uploads and the post-interview report fetch.
- Verification:
  - `GET /api/v1/orgs/772debd4-.../scorecards/results` returned the demo result: `Test Candidate`, `Senior Backend Developer`, `Senior Backend Scorecard`, weighted score `7.57`, status `completed`.
  - Added `test_scorecard_results_route_is_registered` to guard the route surface.

## 15. Department alias cleanup

- Removed the legacy `department_id` field from `InterviewBrain` and the V4 `InterviewState` TypedDict.
- Removed `department_id` from the WebSocket start, answer, and status payloads; clients now use `org_id`.
- Removed the deprecated `department_id` / `department_name` parameters from:
  - `build_interview_intelligence()`
  - `build_company_brain()` and the company-brain cache
  - `build_role_context()`
  - the `/api/v1/intelligence/build` request schema
- `/api/v1/intelligence/build` now passes `org_id` through to the builder instead of ignoring it.
- Renamed the Pinecone helpers to `store_org_knowledge` / `delete_org_knowledge`; the `department_{org_id}` namespace prefix is retained so existing vectors remain readable.
- `org_content.py` and `scripts/index_org_documents.py` use the organization-named helpers.
- Removed `department_id` from the frontend interview types, controller, service, and WebSocket start payload.
- Practice detection now checks `org_id` only (`InterviewRoom`, `ConductorRoom`).
- Removed the broken legacy dev scripts `build_brain_demo.py`, `verify_brain_profiles.py`, and `setup_role_demo.py`.
- Added `test_ws_reconnect_resumes_existing_state`: closing and reopening the socket resumes the stored question instead of rebuilding the interview.

## 16. Company context naming

- Renamed the RAG state fields `department_context` → `company_context` and `department_requirements` -> `company_requirements` in the brain and V4 state.
- Renamed `department_context_node` to `company_context_node` and updated the engine lifecycle, session start, and tests.
- Updated the phase prompts to refer to the company instead of a department.
- The default interview flow is now `practice` instead of the legacy `department`.
- The prompt warm-up now passes `company_context` instead of `department_context`.
- Renamed the prompt helper parameter that feeds `company_context`-adjacent RAG text to `organization_context`.

## Verification

- Backend tests: `1020 passed` (default suite, integration excluded), including:
  - `tests/test_org_standardization.py` guards the organization routes, the removal of `/departments`, the IT-role analytics route, the admin endpoints, and the template response shape.
  - `tests/test_report_context.py` covers candidate and organization context in the report payload.
  - Existing application/invite, V5 persistence, and WebSocket protocol tests pass with the new template/scorecard fields.
- Opt-in DB integration test: `1 passed` with `PYTEST_USE_DB=1 pytest -m integration tests/integration/test_scorecard_pipeline.py`.
- The integration test cleans up its organization, user, session, templates, scorecard, evidence, and result rows.
- Frontend TypeScript: clean.
- API smoke tests:
  - Organization documents, sessions, templates: 200.
  - Analytics overview and sessions by IT role: 200.
  - `/api/v1/departments`: 404.
  - Admin email templates, audit logs, LLM status, LLM usage: 200.
- Demo database check:
  - Organizations: 1 (Nova AI), each with one active owner.
  - Users: 2 (admin + Nova owner).
  - Candidate profiles: 1 (`candidate@test.com`), verified.
  - Organization documents: 7.
  - Session: completed, engine v5, phase `summary`.
  - Scorecard result: 1 row, template `Senior Backend Scorecard`, weighted score 7.57.
  - Application: CV uploaded, fit completed, organization invited, candidate accepted.
- Demo interview:
  - Session `2b6ed1ba-66b2-41be-9aab-2de97ad4d8bd`.
  - 14 questions, verdict `hire`, score 7.57.
  - Scorecard weighted score 7.57.
  - `scorecard_results`: 1.
- Simulation harness (`senior-backend-developer`, 14 questions):
  - strong: `lean_hire`, `hire` (hire-side 2/2).
  - bluffer: `lean_no_hire`, `insufficient_evidence` (hire-side 0/2).
  - weak: `lean_no_hire`, `no_hire` (hire-side 0/2).
  - awkward: `lean_no_hire` on the valid run; the second run crashed on provider connection errors and was discarded.

## Admin credentials

- `admin@test.com` / `Admin123!` (system admin)
- `nova@test.com` / `Admin123!` (organization owner)
- `candidate@test.com` / `Test123!` (candidate)

## Follow-ups

- Optional: give the awkward persona a second valid simulation run when the LLM provider is stable. The rerun was stopped on request to save time.
- Optional: update the static demo interview text in `frontend/src/data/realInterviews.ts` that still mentions departments.
- Keep demo/test data separate from production data before a real launch.

## Deploy branches (2026-11-19)

- `dev` is where work happens. Pushing it deploys nothing to production.
- `main` is the stable branch. Vercel builds the frontend from `main` (Production). Merging `dev` into `main` also starts the CI workflow.
- `prod` is a deploy-only branch for Render: just `app/`, `prompts/`, `alembic/`, `alembic.ini`, `requirements.txt`, `runtime.txt`, `.env.example` and `render.yaml`, with an allow-list in its `.gitignore`. Never merge `main` into it.
- The "Sync prod" workflow copies those deploy files from `main` into `prod` after CI passes on a push to `main`; the push to `prod` is what redeploys Render. It can also be run by hand from the Actions tab.
- `render.yaml` exists only on `prod`; edit it there. Render needs `PYTHON_VERSION=3.12.6` set in the service's Environment.
- Known issue: the backend job in CI fails on GitHub's Linux runner (it has since at least 2026-11-07) although all tests pass locally, so Sync prod is skipped until that is fixed.
