# 04 — Database Schema (used by the flow)

> Last updated: 2026-08-09 · Tag: [AURA-1.3][T3-calibration-ranking]
> Folds in `docs/engine-schema-audit.md` (kept as the source of truth at repo level).
> All persistence is **best-effort** — a DB failure never breaks an interview.

## Tier A — V5 reasoning core (written every turn / at finalize)

| Table | Columns used | Columns NOT used | Benefit |
|---|---|---|---|
| `interview_brain` | `session_id`, `version`, `current_hypotheses`, `evidence_summary`, `competency_scores`, `difficulty_profile`, `decision_state`, `brain_metadata`, `created_at`, `updated_at` | — | Authoritative durable brain snapshot each turn; powers `/summary` and `/intelligence/brain/{sid}` |
| `evidence_graph` | `session_id`, `nodes`, `edges`, `version`, `created_at`, `updated_at` | — | Persisted evidence→hypothesis/competency graph (brain-view source) |
| `interview_timeline` | `session_id`, `event_type`, `question_number`, `event_data`, `created_at` | — | `brain_snapshot` replay; drives frontend graph animation |
| `hypotheses` | `id`, `session_id`, `statement`, `competency`, `direction`, `confidence`, `supporting_evidence`, `contradicting_evidence`, `status`, `last_updated` | `created_at` (default only) | Hypothesis ledger the director probes against |
| `interview_objectives` | `id`, `session_id`, `competency`, `dimension`, `hypothesis_id`, `hypothesis_statement`, `hypothesis_confidence`, `status`, `evidence_ids`, `priority` | `created_at` (default only) | Probe→satisfied lifecycle per question |
| `observations` | `session_id`, `question_number`, `type`, `value`, `evidence`, `pattern`, `risk_signal`, `created_at` | — | Behavioral risk signals (hedging, latency, certainty shifts) |
| `consistency_checks` | `session_id`, `dimension`, `answers_compared`, `consistency_score`, `contradictions`, `check_type`, `assessment`, `score`, `confidence`, `evidence`, `checked_at` | `created_at` (default only) | Cross-answer consistency validation at finalize |
| `scorecard_results` | `session_id`, `scores`, `weighted_score` | `template_id` | Final per-competency scorecard |
| `calibration_feedback` | `session_id` (unique), `org_id`, `department_id`, `job_role`, `predicted_verdict`, `predicted_score`, `difficulty_reached`, `role_floor`, `actual_outcome` (default `no_feedback`), `notes`, `recorded_at` | — | T4 calibration loop: recruiter-recorded post-hire outcome vs the session's predicted verdict. Written on feedback (not at finalize); predicted side snapshotted from `interview_brain.brain_metadata.calibration_state` |
| `v4_session_state` | `session_id`, `state`, `state_version`, `updated_at` | — | Durable checkpoint of live engine state (crash recovery) |
| `interview_events` | `session_id`, `seq`, `event_type`, `payload`, `created_at` | `id` (sequence default) | Append-only event log |

## Tier B — Transcript tables (per answered turn + summary read)

| Table | Columns used | Columns NOT used | Benefit |
|---|---|---|---|
| `interview_sessions` | `id`, `org_id`, `department_id`, `candidate_profile_id`, `job_role`, `session_type`, `interaction_mode`, `status`, `current_phase`, `current_question_number`, `total_questions`, `scorecard_template_id`, `started_at`, `created_at`, `updated_at`, `final_score`, `final_feedback`, `ended_at`, `engine_version` | — | The session anchor + completion state |
| `interview_messages` | `id`, `session_id`, `role`, `message_type`, `content`, `question_number`, `phase`, `score`, `created_at` | `follow_up_question`, `evaluated_at` | Full Q/A transcript for summary/report |
| `interview_evaluations` | `id`, `session_id`, `message_id`, `score`, `technical_score`, `communication_score`, `strengths`, `weaknesses`, `created_at` | `feedback_detail` (always NULL in flow), `evaluated_at` | Per-answer scores + strengths/weaknesses |
| `evidence_store` | `id`, `session_id`, `competency`, `dimension`, `score`, `confidence`, `evidence_text`, `source_question`, `question_number`, `hypothesis_id`, `hypothesis_relevance`, `evidence_metadata`, `created_at` | — | Raw claim evidence feeding the brain |

## Tier C — Intelligence bundle (written once at session start)

| Table | Columns used | Columns NOT used | Benefit |
|---|---|---|---|
| `company_brains` | `session_id`, `department_id`, `company_name`, `industry`, `company_vision`, `values`, `technical_stack`, `culture`, `success_signals`, `red_flags`, `source_documents`, `snapshot` | `source_version` | Company DNA steering question tone/topics |
| `interview_blueprints` | `session_id`, `department_id`, `role`, `objectives`, `phases`, `hypothesis_template`, `evidence_requirements`, `snapshot` | — | Role plan → evidence requirements |
| `candidate_brains` | `session_id`, `candidate_id`, `full_name`, `resume_summary`, `skills`, `strengths`, `weaknesses`, `work_history`, `inferred_seniority`, `persona`, `snapshot` | — | Initial hypotheses from resume/profile |
| `scorecards` | `session_id`, `department_id`, `role`, `competencies`, `required_level`, `snapshot` | — | Scorecard taxonomy for competency resolution |
| `candidate_evidence_requirements` | `session_id`, `competency`, `dimension`, `required_probes`, `evidence_level`, `snapshot` | — | Min-evidence gates per competency |

## Tier D — Auth / org / listing (mostly reads, some writes)

| Table | Columns used | Columns NOT used | Benefit |
|---|---|---|---|
| `users` | `id`, `email`, `password_hash`, `name`, `is_active` (read), `created_at` | `avatar_url`, `is_admin` | Org login (seeded) |
| `organizations` | `id`, `name`, `slug` | `logo_url`, `description`, `website`, `settings`, `is_active` | Org resolution for role context |
| `org_users` | `id`, `org_id`, `user_id`, `role` | `invited_by`, `joined_at` | Login memberships (role=owner) |
| `refresh_tokens` | `id`, `user_id`, `token_hash`, `expires_at` | `revoked` (only on refresh/logout), `created_at` | Org token session |
| `departments` | `id`, `org_id`, `name` | `website`, `description`, `created_at` | Role/company context |
| `candidate_profiles` | `id`, `email`, `name`, `password_hash`, `is_registered`, `is_verified`, `skills`, `profile_data`, `created_at`, `updated_at` | `phone`, `resume_url`, `google_id`, `verified_at`, `verification_token_hash`, `verification_sent_at` | Candidate auth + profile → hypotheses |
| `candidate_refresh_tokens` | `id`, `candidate_id`, `token_hash`, `expires_at`, `revoked`, `created_at` | — | Candidate token rotation |
| `candidate_sessions` | `id`, `candidate_id`, `session_id`, `created_at` | — | Practice-session linking |
| `public_interviews` | `id`, `org_id`, `department_id`, `title`, `description`, `interview_mode`, `is_open`, `max_candidates`, `skills_required`, `rich_description`, `style_name`, `created_at` | `template_id`, `verification_method`, `token`, `token_expires_at`, `starts_at`, `expires_at` | The marketplace listing being interviewed against |
| `public_interview_submissions` | `id`, `public_id`, `session_id`, `candidate_email`, `candidate_name`, `started_at` | `completed_at`, `created_at` | Candidate ↔ listing start tracking |
| `audit_log` | `org_id`, `user_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `created_at` | `details` | Listing create/update audit trail |

## Tier E — NOT touched by this flow

`alembic_version` · `interview_slots`, `slot_availability`, `bookings`
(scheduling) · `candidate_invitations` (email invite) · `candidate_saved_listings`
· `org_invitations`, `user_password_reset_tokens`,
`candidate_password_reset_tokens` · `interview_templates` (FK target only) ·
`scorecard_templates` (FK target only) · `candidate_documents` (needs resume
upload) · `department_documents` (read only via Pinecone RAG when a department
has docs — skipped with no docs).

## Audit caveats

- `public_interviews` / `audit_log` / `rich_description` write only in the
  "create new listing" branch of the autopilot; an existing listing is reused
  read-only.
- `department_documents` is conditionally read via `app/rag/pinecone_store` →
  `get_department_retriever` inside `app/intelligence/company_intelligence_builder.py`
  only when `department_id` is set and documents exist.
- All persistence is best-effort by design.
