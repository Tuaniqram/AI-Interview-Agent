# Copy-Paste Handoff Prompt for Claude Terminal

> Paste the section below into the Claude terminal after opening this repository.

---

You are continuing the AI Interview Agent repository at `D:\projectiqram\AI\AI-Interview-Agent`.

## Read first

Read these files before changing code:

1. `CLAUDE_APPLICATION_FLOW_HANDOFF.md` — authoritative design for the work below
2. `CLAUDE_HANDOFF.md` — repository state, scope rules, known gaps
3. `CLAUDE_API_CATALOG.md` — mounted/unmounted API map
4. `CLAUDE_PROMPT_CATALOG.md` — prompt ownership and planned application-fit prompt
5. `SYSTEM_GUIDE.md` — end-to-end system and user flows
6. `docs/it-scope/README.md`, `docs/it-scope/01-scope-change.md`, `docs/it-scope/02-glossary.md`, `docs/it-scope/04-final-table-list.md`, and `docs/it-scope/schema.sql`

## Objective

Finish the candidate application flow and all surrounding frontend layouts so the system is fully functional end-to-end.

Scope included:
- guest and logged-in candidate applications
- required CV handling
- automatic application fit evaluation using organization documents and IT role competencies
- organization applicant review
- email invitations
- guest invite acceptance
- account claiming and candidate history
- all frontend pages/routes/layouts for these flows
- targeted tests and documentation updates

Scope excluded:
- hardening the interview engine itself
- redesigning the interview runtime
- start/practice interview engine quality work (deferred to a later session)
- voice/avatar/camera feature work
- full legacy test-suite cleanup unless it directly blocks this flow

## Locked product decisions

1. Guests apply with email, name, and a required CV.
2. Logged-in candidates use their profile CV; if none exists, they must upload one during apply.
3. Every application is stored in `public_interview_submissions`; do not create an `applications` or `guest_candidates` table.
4. Guest applicants are stored as real `candidate_profiles` with `is_registered = false`.
5. Applications are evaluated automatically after submit using:
   - public interview listing
   - IT role and `role_competencies`
   - organization documents through RAG
   - candidate CV text and profile
6. The engine produces `fit_score` (0–10), `fit_summary`, and `fit_breakdown`.
7. The organization reviews applicants and decides whom to invite. No automatic rejection.
8. Invites send email and also appear in the candidate's My Applications when logged in.
9. A guest can accept an invite and take the interview without creating an account.
10. Registering with the same email claims the guest profile and history after email verification.
11. PDF CV only for v1 unless the user explicitly asks for DOCX.

## Current blockers you must fix

- `app/candidates/service.py::register` returns `409` for any existing email; it must claim `is_registered = false` profiles instead.
- `app/candidates/service.py::google_login` does not mark an existing guest profile as registered.
- `POST /api/v1/candidates/me/resume` requires auth and does not return the new document ID; guest CV upload and application linking need a helper.
- `app/marketplace/service.py::apply_to_public_interview` does not require or store a CV and does not evaluate fit.
- `app/marketplace/service.py::invite_application` creates a session/invite token but sends no email.
- `.env` has no `RESEND_API_KEY`; email sending is disabled until configured.
- Organization documents are stored under `department_{org_id}` but runtime/evaluation still uses `department_id=None`; organization RAG must be wired through `org_id`.
- `frontend/src/pages/opportunity-hub/InterviewDetail.tsx` uploads CV with a raw unauthenticated `fetch` and does not require a CV.
- `GET /api/v1/marketplace/applications/me` exists but is not gated by `require_verified_candidate`.
- There is no public application-invite page and no public invite-token response endpoint.

## Implementation phases

### Phase 1 — Identity, CV, apply

Backend:
- Add an Alembic migration after `f4a5b6c7d8e9` adding to `public_interview_submissions`:
  - `fit_status` text not null default `pending`
  - `fit_breakdown` JSONB nullable
  - `fit_evaluated_at` timestamptz nullable
  - `fit_error` text nullable
- Add a reusable resume helper that:
  - validates PDF
  - saves the file
  - extracts text
  - creates a `candidate_documents` row
  - sets `candidate_profiles.resume_url`
  - returns the new `CandidateDocument.id`
- Change the apply contract to multipart:
  - email/name for guests
  - optional candidate bearer token
  - required CV when the profile has no CV
  - `resume_document_id` optional when already uploaded
- Enforce CV server-side; return `400 CV is required` when missing.
- Link `public_interview_submissions.resume_document_id`.
- Set `fit_status = pending` on apply.
- Modify candidate registration to claim unregistered profiles by email.
- Modify Google login to claim and mark existing guest profiles.
- Gate `GET /marketplace/applications/me` with `require_verified_candidate`.

Frontend:
- Update `frontend/src/pages/opportunity-hub/InterviewDetail.tsx`:
  - prefill name/email for logged-in candidates
  - require CV for guests and for profiles without one
  - submit multipart through `marketplaceService`
  - remove the raw `fetch` CV upload
  - show a clear submitted/check-email state
- Update `frontend/src/types/marketplace.ts`, `marketplaceService.ts`, and `candidateService.ts` as needed.
- Finish the candidate registration claim messaging if needed.

### Phase 2 — Automatic evaluation and organization review

Backend:
- Add `org_id` support to company-brain/intelligence builders and RAG:
  - add `get_org_retriever(org_id)` in `app/rag/pinecone_store.py`
  - keep compatibility with existing `department_{org_id}` document namespaces
  - update `app/agents/init/company_context.py`
  - update `app/intelligence/company_intelligence_builder.py`
  - update `app/intelligence/__init__.py`
  - pass `org_id` from `app/api/interview_ws.py` instead of `None`
- Add `prompts/evaluation/application_fit.md` using the inputs and JSON contract in `CLAUDE_PROMPT_CATALOG.md`.
- Add `app/marketplace/fit_evaluation.py::evaluate_application_fit(application_id, db)`:
  - load application, public interview, organization, IT role, role competencies
  - load candidate profile and latest `candidate_documents.extracted_text`
  - retrieve organization docs through org-scoped RAG
  - run `analyze_resume` and `match_candidate_to_role`
  - call the LLM with `application_fit.md`
  - validate JSON
  - persist fit fields
  - set `fit_status = completed` or `failed`
- Trigger evaluation after apply using FastAPI `BackgroundTasks`; do not block the HTTP response.
- Add `POST /api/v1/marketplace/applications/{application_id}/evaluate` for org owner re-run.
- Extend `ApplicationResponse` with fit fields, `has_resume`, and `resume_filename`.
- Ensure org resume access is authorized by application ownership.

Frontend:
- Update `frontend/src/pages/org/Applications.tsx`:
  - CV download
  - fit status/score/summary/breakdown
  - re-run evaluation
  - invite/reject/hire actions
- Update candidate applications page to show fit status and CV.

### Phase 3 — Invite email and guest acceptance

Backend:
- Add `RESEND_API_KEY` to `.env` if the user provides one; otherwise keep email disabled and log clearly.
- Add email templates under `app/emails/templates/`:
  - `application_received.html`
  - `application_invitation.html`
  - `application_outcome.html` optional
- On invite:
  - create/keep the session and `invite_token`
  - send the invite email to the candidate
  - do not roll back the invite if email fails
- Add public endpoints:
  - `GET /api/v1/marketplace/application-invitations/{token}`
  - `POST /api/v1/marketplace/application-invitations/{token}/respond`
- Resolve invite tokens through `interview_sessions.invite_token` joined to `public_interview_submissions.session_id`.
- Do not use the public listing token for application invites.
- Guest accept must return the session ID and allow starting the interview.

Frontend:
- Add `/application-invite/:token` page:
  - works without login
  - shows organization, role, candidate name/email
  - accept/decline
  - on accept navigate to `/interview/{session_id}`
- Add the route in `frontend/src/routes/index.tsx`.
- Keep the logged-in My Applications accept/decline flow.

### Phase 4 — Account history and layout completion

Backend:
- Ensure claimed profiles keep all applications, CVs, sessions, and scores.
- Keep unverified accounts from reading history.
- Add outcome email if time allows.

Frontend:
- Finish all layout/routes touched by this flow:
  - candidate registration claim state
  - My Applications
  - organization Applications
  - application invite page
  - any empty/loading/error states
- Fix any obvious broken links or dead routes in these pages.
- Do not redesign the interview room.

## Verification

Run:

```powershell
python -m compileall -q app
python -c "import app.main; print('import ok')"
& "frontend\node_modules\.bin\tsc.cmd" --noEmit -p frontend
```

Add or run targeted tests for:
- guest apply without CV -> 400
- guest apply with CV -> profile + document + linked submission
- logged-in apply without CV -> 400
- logged-in apply with CV -> linked document
- claim-on-register preserves profile ID and history
- Google claim
- invite email is attempted
- public invite verify/accept/decline
- org RAG retrieval receives org documents
- application evaluation success/failure paths

Do not run the full legacy test suite unless you first update it for the 30-table schema.

## Guardrails

- Do not create separate application or guest tables.
- Keep `public_interview_submissions` as the application record.
- Keep `candidate_profiles.email` unique.
- Do not add departments, `org_users`, `org_invitations`, or `candidate_sessions`.
- Do not write to removed evaluation tables; use `interview_intelligence`.
- Preserve existing candidate profiles, documents, and sessions in migrations.
- Back up the database before destructive migrations.
- Keep `resumes/` untracked.
- Update `CLAUDE_API_CATALOG.md`, `CLAUDE_PROMPT_CATALOG.md`, and `SYSTEM_GUIDE.md` when contracts change.
- Commit only when the user asks.

## Start here

Start with Phase 1. Finish Phase 1 completely, verify it, then proceed to Phase 2. Keep the application flow usable at each phase boundary.
