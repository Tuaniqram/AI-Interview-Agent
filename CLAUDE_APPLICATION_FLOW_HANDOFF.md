# Claude Handoff — Candidate Application Flow (CV, Fit, Invite, Account Claim)

> Last updated: 2026-11-06
> Repository: `D:\projectiqram\AI\AI-Interview-Agent`
> Status: design agreed; implementation not started
> Read this with `CLAUDE_HANDOFF.md`, `CLAUDE_API_CATALOG.md`, and `CLAUDE_PROMPT_CATALOG.md`.

## 1. Goal

Make the Opportunity Hub application flow complete:

1. Guest applicants can apply with email, name, and a required CV.
2. Logged-in candidates apply with their profile and a required CV.
3. The system automatically evaluates the application against the organization documents, IT role, role competencies, and CV.
4. The organization sees an applicant list with CV, fit score, fit summary, and status.
5. The organization invites candidates by email.
6. Invited candidates can accept/decline and take the interview.
7. A guest who later creates an account with the same email keeps their applications, CV, interviews, and scores.
8. All frontend layouts/routes for the application, applicant-review, invite, and account-history flows must be finished.
9. Interview-engine hardening for start/practice is out of scope for this handoff. The application flow must hand off cleanly to the existing runtime, but engine quality work is a later session.

## 2. Locked Product Decisions

These are agreed. Do not re-litigate unless the user changes them.

1. **Guest can interview without creating an account.** The emailed invite link is the access path.
2. **Account creation with the same email claims the guest profile after email verification.** Same `candidate_profiles.id` is preserved.
3. **CV is required for every application.**
   - Guest: CV file must be uploaded during apply.
   - Logged-in candidate: use the CV already on the profile; if absent, require upload during apply and save it to the profile.
4. **PDF only for v1.** Current code supports only `.pdf`. Add DOCX only if explicitly requested.
5. **No automatic rejection.** The engine produces a fit score and summary; the organization decides whether to invite, reject, or hire.
6. **Evaluation runs automatically on apply.** The organization list shows `Evaluating...` until completed. The organization may re-run evaluation if it fails.
7. **Guest applications are stored as real candidate profiles**, not a separate guest table.
8. **Do not create a separate applications table.** `public_interview_submissions` remains the application record.

## 3. Current Code Reality

This is what exists today. Several pieces are partial or broken.

### 3.1 Identity

- `candidate_profiles.email` is unique: `app/models/db.py:315`.
- Anonymous apply creates a `CandidateProfile` with `is_registered=False`: `app/marketplace/service.py::apply_to_public_interview`.
- Registration rejects an existing email with `409`: `app/candidates/service.py::register`.
- Google login attaches `google_id` to an existing profile but does not mark it registered: `app/candidates/service.py::google_login`.

Consequence: a guest applicant cannot later register with the same email until the claim behavior is implemented.

### 3.2 CV / resume

- `CandidateDocument` exists: `app/models/db.py:1110`.
- `candidate_profiles.resume_url` exists: `app/models/db.py:318`.
- `public_interview_submissions.resume_document_id` exists: `app/models/db.py` (submission model).
- `POST /api/v1/candidates/me/resume` requires candidate auth, accepts PDF only, and returns the profile, not the new document ID: `app/api/v1/candidates.py:351`.
- `app/candidates/resume_service.py` supports PDF only; `ALLOWED_EXTENSIONS = {".pdf"}`.
- The public apply page uploads with a raw `fetch` and no auth header: `frontend/src/pages/opportunity-hub/InterviewDetail.tsx`.
- `ApplyRequest.resume_document_id` exists but the current UI never supplies it: `app/marketplace/schemas.py:103`.

Consequence: guest CV upload is not supported, and the current frontend CV upload is unreliable even for logged-in candidates.

### 3.3 Evaluation

- `apply_to_public_interview` only creates/updates the submission; it does not evaluate fit.
- `set_application_fit` is manual and org-triggered: `app/marketplace/service.py`.
- Org applications page exists: `frontend/src/pages/org/Applications.tsx`.
- Candidate applications page exists: `frontend/src/pages/candidate/Applications.tsx`.
- Candidate application list endpoint exists: `GET /api/v1/marketplace/applications/me` in `app/api/v1/marketplace.py`.
- The org applicant UI does not download/show CVs or display auto-evaluation details.

### 3.4 Organization RAG

This is the biggest blocker for “evaluate through company org docs”.

- Organization documents are stored in Pinecone under namespace `department_{org_id}`: `app/api/v1/departments.py::_process_document`.
- Runtime retrieval is still department-based:
  - `app/rag/pinecone_store.py::get_department_retriever`
  - `app/agents/init/company_context.py`
  - `app/intelligence/company_intelligence_builder.py`
- The interview WS path starts with `department_id=None`: `app/api/interview_ws.py::_start_v4_engine`.
- `build_interview_intelligence` and `build_company_brain` still accept `department_id`, not `org_id`: `app/intelligence/__init__.py`, `app/intelligence/company_intelligence_builder.py`.

Consequence: organization documents are effectively not used by the current evaluation or interview runtime.

### 3.5 Invite and email

- `invite_application` creates an `interview_sessions` row with `invite_token` and `invite_expires_at`: `app/marketplace/service.py`.
- It does not send email.
- `.env` currently has no `RESEND_API_KEY`; `app/services/email.py` disables sending when absent.
- Existing email templates live under `app/emails/templates/`:
  - `invitation.html`
  - `booking_confirmation.html`
  - `password_reset.html`
  - `verification.html`
  - `org_invitation.html`
- There is no application-invitation email template yet.
- `CandidateInvitation` is a separate direct-invite table/API (`app/api/v1/invitations.py`). Do not confuse it with application invites. Application invites already have `interview_sessions.invite_token`.

### 3.6 Frontend

- Public/candidate apply: `frontend/src/pages/opportunity-hub/InterviewDetail.tsx`.
- Candidate applications: `frontend/src/pages/candidate/Applications.tsx`.
- Org applications: `frontend/src/pages/org/Applications.tsx`.
- Candidate routes: `frontend/src/routes/index.tsx`.
- Candidate nav: `frontend/src/layout/CandidateShell.tsx`.
- Org nav: `frontend/src/layout/AppShell.tsx`.
- Marketplace types: `frontend/src/types/marketplace.ts`.
- Marketplace service: `frontend/src/services/marketplaceService.ts`.
- Candidate service: `frontend/src/services/candidateService.ts`.

## 4. Target Domain Flow

### 4.1 Guest applies

1. Candidate opens an Opportunity Hub listing.
2. Form asks for email, name, and CV (required).
3. Backend:
   - find or create `candidate_profiles` by email with `is_registered=False`
   - create a `candidate_documents` row with extracted text
   - set `candidate_profiles.resume_url`
   - create/update `public_interview_submissions`
   - set `resume_document_id`
   - set `status='applied'`, `org_decision='pending'`, `candidate_response='pending'`, `outcome='pending'`
   - set `fit_status='pending'`
4. Kick off automatic fit evaluation.
5. Response tells the candidate the application was submitted and an email will follow.

### 4.2 Logged-in candidate applies

1. Form prefills name/email from profile.
2. If profile has no CV, show a required CV upload and save it to the profile.
3. Backend uses the authenticated `candidate_profile_id`.
4. The rest is the same as guest apply.
5. Application immediately appears in My Applications.

### 4.3 Automatic fit evaluation

Run asynchronously after application commit.

Inputs:
- public interview: title, description, skills, level, IT role
- IT role and `role_competencies`
- organization documents via RAG
- candidate CV extracted text
- candidate profile data

Output:
- `fit_score` 0–10
- `fit_summary`
- `fit_breakdown` JSON:
  - matched competencies
  - missing competencies
  - resume strengths
  - risks
  - recommended interview probes

On failure:
- `fit_status='failed'`
- keep the application usable
- allow org re-run

### 4.4 Organization reviews applicants

Applicant list must show:
- candidate name/email
- applied role
- CV download
- fit status (`pending`, `running`, `completed`, `failed`)
- fit score and summary
- application status
- actions: Invite, Reject, later Hire

### 4.5 Invite by email

On invite:
1. Create the session (current behavior) with `invite_token`.
2. Set application to `org_decision='invited'`, `status='interview_offered'`, `invited_at=now`.
3. Send an email with a link:
   `${APP_URL}/application-invite/${invite_token}`
4. Logged-in candidates also see the invite in My Applications.

### 4.6 Candidate accepts

The invite link must work without an account.

1. Public page loads invite by token.
2. Shows organization, role, and current status.
3. Candidate clicks Accept or Decline.
4. Accept:
   - `candidate_response='accepted'`, `status='interview_accepted'`
   - session remains linked to the candidate profile (guest or registered)
   - route to `/interview/{session_id}`
5. Decline:
   - `candidate_response='declined'`, `status='interview_declined'`
   - cancel the session

### 4.7 Account creation after guest activity

If a guest later registers with the same email:

- Claim the existing profile instead of returning `409`.
- Set `password_hash`, `is_registered=True`.
- Keep the same `candidate_profiles.id`.
- Send the normal verification email.
- After verification, applications, CV, interviews, and scores appear in the account.

Google login with the same email must also claim the profile.

If the user registers with a different email, no claim occurs.

## 5. Status Values

Application `status`:
- `applied`
- `screening`
- `evaluated`
- `interview_offered`
- `interview_accepted`
- `interview_declined`
- `interviewed`
- `hired`
- `rejected`
- `withdrawn`

`fit_status`:
- `pending`
- `running`
- `completed`
- `failed`

`org_decision`:
- `pending`
- `invited`
- `rejected`

`candidate_response`:
- `pending`
- `accepted`
- `declined`

`outcome`:
- `pending`
- `hired`
- `rejected`

## 6. Database Changes

Add to `public_interview_submissions`:

| Column | Type | Purpose |
|---|---|---|
| `fit_status` | `Text NOT NULL DEFAULT 'pending'` | Async evaluation state |
| `fit_breakdown` | `JSONB NULL` | Structured fit details |
| `fit_evaluated_at` | `TIMESTAMPTZ NULL` | Completion timestamp |
| `fit_error` | `Text NULL` | Failure reason for retries |

Existing columns to use:
- `resume_document_id`
- `fit_score`
- `fit_summary`
- `status`
- `org_decision`
- `candidate_response`
- `invited_at`
- `outcome`

No new table is required for this flow. Do not create `applications` or `guest_candidates`.

Migration requirements:
- Generate a new Alembic revision after `f4a5b6c7d8e9`.
- Backfill existing rows with `fit_status='pending'`.
- Preserve all existing data.

## 7. API Changes

### 7.1 Apply with CV

Recommended contract:

`POST /api/v1/marketplace/interviews/{interview_id}/apply`

Content type: `multipart/form-data`

Fields:
- `candidate_email` (required for guest; ignored/validated for logged-in)
- `candidate_name` (required for guest)
- `resume` (file; required when profile has no CV)
- `resume_document_id` (optional; used when the CV was already uploaded)

Auth: optional candidate bearer token.

Response: `ApplicationResponse` extended with:
- `fit_status`
- `fit_breakdown`
- `fit_evaluated_at`
- `has_resume` boolean
- `resume_filename` optional

Rules:
- Guest without file -> `400 CV is required`.
- Logged-in without profile CV and without file -> `400 CV is required`.
- Logged-in with profile CV and no file -> use existing latest `candidate_documents` row.
- Guest -> create unregistered profile.
- Save CV and link `resume_document_id`.

If changing the existing JSON endpoint is risky, add a parallel multipart endpoint and keep the JSON endpoint only for internal/tests. Do not leave the frontend calling the old JSON path without CV.

### 7.2 Candidate CV endpoints

- `POST /api/v1/candidates/me/resume` — keep, but return `{ profile, document_id }` or add `GET /api/v1/candidates/me/documents`.
- Add a guest-safe internal helper rather than exposing the auth-only endpoint to guests.
- `GET /api/v1/candidates/{candidate_id}/resume` — keep, but require that the org owns an application from that candidate; do not leave it pending auth.

### 7.3 Evaluation

- Automatic: called by apply.
- Manual re-run: `POST /api/v1/marketplace/applications/{application_id}/evaluate` (org owner).
- Return updated `ApplicationResponse`.

### 7.4 Invite and public acceptance

Keep current:
- `POST /api/v1/marketplace/applications/{application_id}/invite` (org owner)

Add:
- `GET /api/v1/marketplace/application-invitations/{token}` — public; returns org, role, candidate name/email, status, expiry.
- `POST /api/v1/marketplace/application-invitations/{token}/respond` — public; body `{ "response": "accepted" | "declined" }`; validates token/expiry; updates submission; returns session ID.

Token source: `interview_sessions.invite_token` joined to `public_interview_submissions.session_id`.
Do not use the listing token for this.

### 7.5 Candidate applications

- `GET /api/v1/marketplace/applications/me` already exists.
- Gate it with `require_verified_candidate` so unverified claims cannot read history.

## 8. Evaluation Implementation

Add a service, for example:

`app/marketplace/fit_evaluation.py::evaluate_application_fit(application_id, db)`

Steps:

1. Load submission, public interview, organization, IT role, role competencies.
2. Load candidate profile and latest `candidate_documents.extracted_text`.
3. Resolve competencies through the existing resolver:
   - `app/data/competency_resolver.py`
4. Build organization context:
   - add `get_org_retriever(org_id)` in `app/rag/pinecone_store.py`
   - keep the physical namespace compatible with existing `department_{org_id}` documents, or add a dual-read migration
5. Run deterministic matching:
   - `app/intelligence/candidate_matcher.py::match_candidate_to_role`
   - `app/intelligence/resume_analyzer.py::analyze_resume`
6. Build a prompt `prompts/evaluation/application_fit.md` with:
   - role, level, skills
   - organization context
   - candidate profile/CV
   - competency matches/gaps
7. Validate JSON output against a schema.
8. Persist:
   - `fit_score`
   - `fit_summary`
   - `fit_breakdown`
   - `fit_status`
   - `fit_evaluated_at`
9. On error:
   - `fit_status='failed'`
   - `fit_error`
   - log and keep application usable.

Execution:
- Use FastAPI `BackgroundTasks` for v1, like document ingestion.
- Production queue can replace it later.
- Do not block the HTTP apply response on LLM completion.

Required RAG refactor:
- Add `org_id` support to `build_company_brain` and `build_interview_intelligence`.
- Keep `department_id` as a backward-compatible alias only where needed.
- Update `app/agents/init/company_context.py` and `app/api/interview_ws.py` to pass `org_id`, not `None`.
- Ensure the interview runtime itself retrieves org documents too.

## 9. Email and Invite Implementation

Add `RESEND_API_KEY` to `.env`. Without it, email is disabled.

Add templates under `app/emails/templates/`:
- `application_received.html`
- `application_invitation.html`
- `application_outcome.html` (optional)

Invite email variables:
- `CANDIDATE_NAME`
- `ORG_NAME`
- `JOB_ROLE`
- `INVITE_URL`
- `APP_URL`
- `EXPIRES_AT`

Invite URL:
`${APP_URL}/application-invite/${invite_token}`

Behavior:
- Send email on invite for both guest and registered candidates.
- Keep the in-app My Applications entry as the logged-in source of truth.
- Email failure must not roll back the invite; log it and allow resend later.

## 10. Account Claim Implementation

Modify `app/candidates/service.py::register`:

Current:
- existing email -> `409`.

Target:
- existing row and `is_registered=True` -> `409` (real duplicate).
- existing row and `is_registered=False` -> claim:
  - set `password_hash`
  - set/update `name`
  - set `is_registered=True`
  - preserve `id`, `resume_url`, `profile_data`, documents, submissions, sessions
  - send verification
  - return auth response

Modify `google_login`:
- existing guest profile: set `google_id`, `is_registered=True`, `is_verified` from Google data when present.
- preserve profile ID and history.

Security:
- Gate history endpoints behind `require_verified_candidate`.
- Do not expose guest history before email verification.
- If the email is already registered and the password is wrong, normal login failure applies.

## 11. Frontend Changes

### 11.1 Opportunity Hub apply page

`frontend/src/pages/opportunity-hub/InterviewDetail.tsx`

- If logged in, prefill name/email.
- Check profile CV; if absent, require CV upload.
- If guest, require CV upload.
- Remove raw `fetch` CV upload.
- Submit multipart through `marketplaceService`.
- Show success state with:
  - “Application submitted”
  - “Check your email for updates”
  - link to My Applications when logged in.

### 11.2 Candidate applications page

`frontend/src/pages/candidate/Applications.tsx`

- Show fit status/score/summary.
- Show CV filename.
- Show invite status.
- Accept/decline remains.
- Start interview remains when accepted.

### 11.3 New public application-invite page

Add route `/application-invite/:token`.

Page:
- loads invite by token
- shows org, role, candidate name/email
- accept/decline
- on accept, navigate to `/interview/{session_id}`
- works without login

Do not reuse `/public-interview/:token`; that token starts a new interview and is not the application invite token.

### 11.4 Organization applications page

`frontend/src/pages/org/Applications.tsx`

- Add CV download link.
- Add fit status, score, summary, and breakdown.
- Add “Re-run evaluation” when failed.
- Keep invite/reject/hire actions.

### 11.5 Candidate registration

- If the email matches an unregistered guest profile, show a claim message.
- After verification, history is visible.

## 12. Implementation Order

### Phase 1 — Identity, CV, apply

1. Add migration for fit fields.
2. Add resume helper that stores `CandidateDocument` and returns document ID.
3. Change apply to multipart and require CV.
4. Update `InterviewDetail`.
5. Add guest CV path and logged-in profile CV reuse.
6. Add claim-on-register and Google claim.
7. Gate `applications/me` by verified email.

### Phase 2 — Evaluation and org review

1. Refactor RAG to org ID.
2. Add `application_fit.md` prompt.
3. Add `evaluate_application_fit`.
4. Trigger after apply.
5. Extend `ApplicationResponse`.
6. Update org applications UI.
7. Add manual re-run endpoint.

### Phase 3 — Invite email and guest acceptance

1. Add `RESEND_API_KEY`.
2. Add email templates.
3. Send invite email.
4. Add public invite verify/respond endpoints.
5. Add `/application-invite/:token` page.
6. Ensure guest accept starts interview.

### Phase 4 — History and polish

1. Candidate account history after claim.
2. Application status emails.
3. Outcome emails.
4. Analytics counts for applications/evaluations if needed.
5. Cleanup and tests.

## 13. Testing Checklist

Backend:
- Guest apply without CV -> 400.
- Guest apply with CV -> unregistered profile, candidate document, linked submission.
- Logged-in apply with no CV -> 400.
- Logged-in apply with CV -> document saved to profile and linked.
- Auto-evaluation success -> fit fields populated.
- Auto-evaluation failure -> `fit_status='failed'`, application still usable.
- Org list returns CV, fit status, score, summary.
- Invite sends email (mock Resend) and creates session/token.
- Public invite token verifies and accepts/declines.
- Guest invite accept can start the interview.
- Register with same email claims guest profile.
- Register with same email does not create a duplicate.
- Google login with same email claims guest profile.
- Different email does not claim history.
- Unverified claimed account cannot read history.
- Org RAG retrieval returns organization document chunks.
- Interview runtime receives org context.

Frontend:
- Guest apply requires CV.
- Logged-in apply requires CV only when profile lacks one.
- Success state is clear.
- My Applications shows status and invite.
- Org Applications shows CV and fit details.
- Application invite page works without login.
- Candidate registration claim path works.
- `tsc --noEmit -p frontend` passes.

Do not run the full legacy test suite until it is updated for the 30-table schema.

## 14. Guardrails

- Do not create a separate guest/applications table.
- Keep `public_interview_submissions` as the application record.
- Keep `candidate_profiles.email` unique.
- Keep one owner per organization.
- Do not reintroduce departments, `org_users`, `org_invitations`, or `candidate_sessions`.
- Do not write evaluation data to removed tables.
- Do not use the listing token as the application invite token.
- Do not expose candidate history before email verification.
- Preserve existing candidate profiles, documents, and sessions during migration.
- Back up the database before destructive migrations.
- Keep `resumes/` out of git.
- Update `CLAUDE_API_CATALOG.md`, `CLAUDE_PROMPT_CATALOG.md`, and `SYSTEM_GUIDE.md` when contracts change.

## 15. Suggested First Message to Claude

> Read `CLAUDE_APPLICATION_FLOW_HANDOFF.md`, `CLAUDE_HANDOFF.md`, `CLAUDE_API_CATALOG.md`, and `CLAUDE_PROMPT_CATALOG.md`. Implement Phase 1 first: guest/registered CV-required apply, candidate document linking, claim-on-register, and verified application history. Do not create new application or guest tables. Then continue with Phase 2 evaluation/RAG and Phase 3 invite email. Update the API and prompt catalogs as you go.
