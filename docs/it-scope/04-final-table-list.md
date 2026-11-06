# 04 — Final Table List (30 Tables)

> Status: final table set for the IT-only product with one user per organization,
> marketplace, resumes, org documents, evaluation, and accept/reject workflow.
>
> Removed: `departments`, `org_users`, `org_invitations`, `candidate_sessions`,
> scheduling, calibration, and 9 separate evaluation/intelligence tables.
> Added: `organization_documents` (renamed) and `interview_intelligence` (consolidated).
>
> Total: **30 tables**.

## 1. Tenancy, users, and access

| # | Table | Purpose |
|---:|---|---|
| 1 | `organizations` | Tenant root; one owner user; one organization can publish many interviews |
| 2 | `users` | Organization users |
| 3 | `refresh_tokens` | Organization-user refresh tokens |
| 4 | `user_password_reset_tokens` | Organization-user password reset |

## 2. IT documents and catalog

| # | Table | Purpose |
|---:|---|---|
| 5 | `organization_documents` | IT knowledge documents used by RAG; replaces `department_documents` |
| 6 | `it_roles` | IT role catalog, family, and level range |
| 7 | `competencies` | IT-only competency taxonomy |
| 8 | `role_competencies` | Competency weights and required levels per IT role |

## 3. Candidates and resumes

| # | Table | Purpose |
|---:|---|---|
| 9 | `candidate_profiles` | Candidate identity, profile, resume URL |
| 10 | `candidate_refresh_tokens` | Candidate refresh tokens |
| 11 | `candidate_password_reset_tokens` | Candidate password reset |
| 12 | `candidate_documents` | Uploaded resumes and parsed text |
| 13 | `candidate_invitations` | Direct interview invitation for a specific IT role |

## 4. Marketplace and opportunity hub

| # | Table | Purpose |
|---:|---|---|
| 14 | `public_interviews` | Published interview listing; one org can have many |
| 15 | `public_interview_submissions` | Candidate application, fit score, org invite/decision, candidate accept/decline, and interview link |
| 16 | `candidate_saved_listings` | Candidate bookmarks for listings |

## 5. Templates and interview runtime

| # | Table | Purpose |
|---:|---|---|
| 17 | `scorecard_templates` | Organization scorecard definitions |
| 18 | `interview_templates` | Reusable IT-role interview configuration |
| 19 | `interview_sessions` | Interview anchor and IT-role scope lock |
| 20 | `interview_messages` | Full question/answer transcript |
| 21 | `interview_evaluations` | Per-answer evaluation |

## 6. Evaluation and reasoning

| # | Table | Purpose |
|---:|---|---|
| 22 | `evidence_store` | Raw evidence extracted from answers |
| 23 | `hypotheses` | Candidate hypotheses and status |
| 24 | `interview_brain` | Authoritative live reasoning snapshot |
| 25 | `interview_timeline` | Ordered interview events for replay |
| 26 | `interview_intelligence` | Consolidated company, candidate, blueprint, scorecard, evidence requirements, objectives, consistency, observations, and evidence graph as JSONB |
| 27 | `scorecard_results` | Final per-session scorecard |

## 7. Engine durability and audit

| # | Table | Purpose |
|---:|---|---|
| 28 | `interview_events` | Append-only engine event log |
| 29 | `v4_session_state` | Crash-recovery checkpoint |
| 30 | `audit_log` | Append-only audit trail |

## Removed from the previous active set

| Removed table | Replaced by |
|---|---|
| `departments` | `organization_documents` uses `org_id`; interviews use `public_interviews.org_id` |
| `org_users` | `organizations.owner_user_id` |
| `org_invitations` | One user per organization; no teammate invites |
| `candidate_sessions` | `interview_sessions.candidate_profile_id` already links candidate to session |
| `company_brains` | `interview_intelligence.company_context` |
| `candidate_brains` | `interview_intelligence.candidate_context` |
| `interview_blueprints` | `interview_intelligence.blueprint` |
| `scorecards` | `interview_intelligence.scorecard` |
| `candidate_evidence_requirements` | `interview_intelligence.evidence_requirements` |
| `interview_objectives` | `interview_intelligence.objectives` |
| `consistency_checks` | `interview_intelligence.consistency_checks` |
| `observations` | `interview_intelligence.observations` |
| `evidence_graph` | `interview_intelligence.evidence_graph` |
| `interview_slots` | Removed: no frontend scheduling usage |
| `slot_availability` | Removed: no frontend scheduling usage |
| `bookings` | Removed: no frontend scheduling usage |
| `calibration_feedback` | Removed: no frontend calibration usage |

## Key relationship changes

- `organizations.owner_user_id` → `users.id`; one owner user per organization
- `organization_documents.org_id` → `organizations.id`
- `interview_templates.org_id` → `organizations.id`; `interview_templates.it_role_id` → `it_roles.id`
- `interview_sessions.org_id` → `organizations.id`; no `department_id`
- `candidate_invitations.org_id` → `organizations.id`; `it_role_id` → `it_roles.id`
- `public_interviews.org_id` → `organizations.id`; `it_role_id` → `it_roles.id`; no `department_id`
- `public_interview_submissions` adds `candidate_profile_id`, `resume_document_id`, `status`, `fit_score`, `fit_summary`, `org_decision`, `org_decided_by`, `org_decided_at`, `candidate_response`, `candidate_responded_at`, `invited_at`, `outcome`, `outcome_decided_by`, `outcome_decided_at`; `session_id` becomes nullable so a candidate can apply before interviewing.
- `interview_intelligence.session_id` → `interview_sessions.id` (one row per session)

## Candidate and organization acceptance flow

1. **Candidate applies from OH**
   - Reads open `public_interviews`.
   - Submits profile + resume.
   - `public_interview_submissions.status = 'applied'`, `org_decision = 'pending'`, `candidate_response = 'pending'`.

2. **Organization evaluates**
   - Compares candidate profile/resume with `organization_documents` and `it_roles` / `role_competencies`.
   - Stores `fit_score` and `fit_summary`.

3. **Organization invites**
   - Creates `interview_sessions` with `it_role_id` and `invite_token`.
   - Sets `session_id`, `org_decision = 'invited'`, `org_decided_by`, `org_decided_at`, `invited_at`, `status = 'interview_offered'`.

4. **Candidate accepts or declines**
   - Accept: `candidate_response = 'accepted'`, `candidate_responded_at = now()`, `status = 'interview_accepted'`.
   - Decline: `candidate_response = 'declined'`, `candidate_responded_at = now()`, `status = 'interview_declined'`.

5. **Interview runs**
   - Session status moves `initiating` → `active` → `completed`.
   - Application status becomes `interviewed`.

6. **Final outcome**
   - Organization sets `outcome = 'hired'` or `'rejected'`, with `outcome_decided_by` and `outcome_decided_at`.
   - This is separate from the earlier invite decision.
