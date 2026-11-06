# 03 — Lean Schema Reference (Superseded)

> **Superseded.** The final 33-table design is in
> [`04-final-table-list.md`](04-final-table-list.md) and [`schema.sql`](schema.sql).
> This file is kept as the earlier lean 25-table reference only.

# 03 — Lean Database Schema (IT-Only Scope)

> Target: PostgreSQL 15+
> Authoritative DDL: [`schema.sql`](schema.sql)
> Seed data: [`seed-it-catalog.sql`](seed-it-catalog.sql)
>
> This is the **lean 25-table** design. It keeps the auth/org/docs/resume tables and
> removes marketplace, scheduling, calibration, and optional intelligence bundles.
> Add those later only when a feature is approved.

## 1. What this schema guarantees

1. **One IT department per organization.**
   `departments.department_type` can only be `IT`; `UNIQUE (org_id)` prevents a second department.
2. **Every interview is tied to an IT role.**
   `interview_sessions.it_role_id` is `NOT NULL` and references `it_roles`.
3. **Every competency is IT-scoped.**
   `competencies.scope` is locked to `IT`.
4. **No free-text role is the source of truth.**
   `job_role_snapshot` is display text; the FK is the authority.
5. **Invites do not need a separate table.**
   An invited session carries a unique `invite_token` and `invite_expires_at`.
6. **Tenant data is owned by an organization.**
   `org_id` on sessions and audit rows.

## 2. Conventions

| Convention | Rule |
|---|---|
| Primary keys | `uuid` with `gen_random_uuid()`; `bigint GENERATED ALWAYS AS IDENTITY` for `departments` |
| Timestamps | `timestamptz NOT NULL DEFAULT now()` |
| Enumerations | `text` + `CHECK` constraints, not PostgreSQL enum types |
| Flexible data | `jsonb` for snapshots, evidence metadata, and brain state |
| Arrays | `uuid[]` for evidence/hypothesis links; `text[]` for evidence dimensions |
| Deletes | `ON DELETE CASCADE` for owned rows; `RESTRICT` for catalog rows; `SET NULL` for optional historical links |
| Email uniqueness | Case-insensitive unique index on `lower(email)` |
| Updated time | `set_updated_at()` trigger on tables with `updated_at`; `set_last_updated()` on `hypotheses` |
| Naming | `snake_case`; indexes use `idx_*`; constraints use descriptive names |

## 3. Entity map

```
Tenancy and access
  organizations ──> org_users ──> users
  organizations ──> org_invitations ──> users
  users ─────────> refresh_tokens
  users ─────────> user_password_reset_tokens

IT department
  organizations ──> departments (one per org, type = IT)
  departments ────> department_documents

IT catalog
  it_roles ──> role_competencies ──> competencies

Candidates
  candidate_profiles ──> candidate_refresh_tokens
  candidate_profiles ──> candidate_password_reset_tokens
  candidate_profiles ──> candidate_documents
  candidate_profiles ──> interview_sessions

Templates
  organizations ──────> scorecard_templates
  departments ────────> interview_templates ──> scorecard_templates

Interview runtime
  interview_sessions ──> interview_messages ──> interview_evaluations
  interview_sessions ──> hypotheses ──> evidence_store
  interview_sessions ──> interview_brain
  interview_sessions ──> interview_timeline

Audit
  organizations ──> audit_log
  users ─────────> audit_log
```

## 4. Table catalog

Legend: `PK` primary key · `FK` foreign key · `UQ` unique · `IX` indexed · `JSONB` PostgreSQL binary JSON.

### 4.1 Tenancy and access

#### `organizations`
Tenant root.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| name | text | Organization name |
| slug | text | UQ |
| logo_url / description / website | text | Optional |
| settings | jsonb | Default `{}` |
| is_active | boolean | Default true |
| created_at / updated_at | timestamptz | Default now() |

#### `users`
Organization users.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| email | text | UQ on `lower(email)` |
| password_hash | text | Required |
| name | text | Required |
| avatar_url | text | Optional |
| is_admin | boolean | Platform admin flag |
| is_active | boolean | Default true |
| created_at / updated_at | timestamptz | Default now() |

#### `org_users`
Membership and access role.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| org_id | uuid | FK → `organizations.id`, CASCADE |
| user_id | uuid | FK → `users.id`, CASCADE |
| role | text | `owner`, `member`, `viewer` |
| invited_by | uuid | FK → `users.id`, SET NULL |
| joined_at | timestamptz | Default now() |

UQ: `(org_id, user_id)`. Indexes: `idx_org_users_org`, `idx_org_users_user`, `idx_org_users_invited_by`.

#### `org_invitations`
Pending organization invitations.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| org_id | uuid | FK → `organizations.id`, CASCADE |
| inviter_id | uuid | FK → `users.id`, CASCADE |
| email | text | Invitee |
| role | text | `owner`, `member`, `viewer` |
| token | text | UQ |
| status | text | `pending`, `accepted`, `expired`, `revoked` |
| expires_at | timestamptz | Required |
| created_at | timestamptz | Default now() |

#### `refresh_tokens`
Organization-user refresh tokens.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK → `users.id`, CASCADE |
| token_hash | text | Hashed token |
| expires_at | timestamptz | Required |
| revoked | boolean | Default false |
| created_at | timestamptz | Default now() |

#### `user_password_reset_tokens`
Organization-user password reset tokens.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK → `users.id`, CASCADE |
| token_hash | text | Hashed token |
| expires_at | timestamptz | Required |
| used | boolean | Default false |
| created_at | timestamptz | Default now() |

### 4.2 IT department and documents

#### `departments`
The single IT department per organization.

| Column | Type | Key / notes |
|---|---|---|
| id | bigint | PK, identity |
| org_id | uuid | FK → `organizations.id`, CASCADE; UQ (one per org) |
| name | text | Default `IT Department` |
| department_type | text | `CHECK (department_type = 'IT')` |
| team_label | text | Optional label such as Platform or Security |
| website / description | text | Optional |
| created_at / updated_at | timestamptz | Default now() |

UQ: `uq_departments_one_it_department_per_org (org_id)`.

#### `department_documents`
IT knowledge documents used by RAG.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| department_id | bigint | FK → `departments.id`, CASCADE |
| filename | text | Required |
| document_type | text | Default `pdf` |
| storage_path | text | Optional object path |
| content_hash | text | Optional dedupe hash |
| pinecone_namespace | text | Required vector namespace |
| created_at | timestamptz | Default now() |

### 4.3 IT catalog

#### `it_roles`
All selectable IT roles. The family and level are checked values, so no separate lookup tables are needed.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| slug | text | UQ, URL-safe role key |
| family | text | One of 23 IT family values |
| name | text | Job title |
| description | text | Optional |
| level_min | text | `intern` … `director` |
| level_max | text | `intern` … `director` |
| is_active | boolean | Retire without deleting history |
| created_at / updated_at | timestamptz | Default now() |

Indexes: `idx_it_roles_family`, `idx_it_roles_name_lower`.

#### `competencies`
IT-only competency taxonomy.

| Column | Type | Key / notes |
|---|---|---|
| id | text | PK (`tech_core`, `behav_teamwork`, …) |
| name | text | Display name |
| category | text | `technical`, `behavioral`, `cognitive`, `experience`, `design`, `product`, `operations`, `general` |
| primary_dimension | text | One of the seven evidence dimensions |
| evidence_dimensions | text[] | Subset of the seven dimensions |
| default_min_evidence | smallint | 0–10 |
| description | text | Optional |
| scope | text | `CHECK (scope = 'IT')` |
| is_active | boolean | Default true |
| created_at | timestamptz | Default now() |

#### `role_competencies`
Baseline competency weight per IT role.

| Column | Type | Key / notes |
|---|---|---|
| role_id | uuid | PK part, FK → `it_roles.id`, CASCADE |
| competency_id | text | PK part, FK → `competencies.id`, CASCADE |
| weight | numeric(5,2) | > 0 and ≤ 100 |
| required_level | text | `intern` … `director`, or null |
| is_core | boolean | Default true |

Index: `idx_role_competencies_competency`.

### 4.4 Candidates

#### `candidate_profiles`
Candidate identity and profile.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| email | text | UQ on `lower(email)` |
| name | text | Required |
| phone / resume_url | text | Optional |
| password_hash | text | Optional for invite-only candidates |
| google_id | text | Optional SSO identity |
| is_registered | boolean | Default false |
| is_verified | boolean | Default false |
| verified_at | timestamptz | Optional |
| verification_token_hash | text | Optional |
| verification_sent_at | timestamptz | Optional |
| skills | text | Quick skill summary |
| profile_data | jsonb | Default `{}` |
| created_at / updated_at | timestamptz | Default now() |

#### `candidate_refresh_tokens`
Candidate refresh tokens.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| candidate_id | uuid | FK → `candidate_profiles.id`, CASCADE |
| token_hash | text | Hashed token |
| expires_at | timestamptz | Required |
| revoked | boolean | Default false |
| created_at | timestamptz | Default now() |

#### `candidate_password_reset_tokens`
Candidate password reset tokens.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| candidate_id | uuid | FK → `candidate_profiles.id`, CASCADE |
| token_hash | text | Hashed token |
| expires_at | timestamptz | Required |
| used | boolean | Default false |
| created_at | timestamptz | Default now() |

#### `candidate_documents`
Candidate resumes and parsed artifacts.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| candidate_id | uuid | FK → `candidate_profiles.id`, CASCADE |
| session_id | uuid | FK → `interview_sessions.id`, SET NULL |
| filename | text | Required |
| document_type | text | Default `resume` |
| content_hash | text | Optional |
| extracted_text | text | Parsed text |
| document_metadata | jsonb | Default `{}` |
| created_at | timestamptz | Default now() |

### 4.5 Templates

#### `scorecard_templates`
Organization-curated scorecards.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| org_id | uuid | FK → `organizations.id`, CASCADE |
| name | text | Required |
| competencies | jsonb | Default `[]` |
| created_at / updated_at | timestamptz | Default now() |

#### `interview_templates`
Reusable IT-role interview blueprint.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| department_id | bigint | FK → `departments.id`, CASCADE |
| it_role_id | uuid | FK → `it_roles.id`, RESTRICT |
| level_code | text | `intern` … `director`, or null |
| name | text | Required |
| job_role_snapshot | text | Display text |
| description | text | Optional |
| interview_style | text | Default `STANDARD` |
| competencies | jsonb | Default `[]` |
| suggested_competencies | jsonb | AI-profiler cache |
| total_questions | integer | 1–100, default 10 |
| scorecard_template_id | uuid | FK → `scorecard_templates.id`, SET NULL |
| created_at | timestamptz | Default now() |

### 4.6 Interview sessions and transcripts

#### `interview_sessions`
The interview anchor and IT-scope lock.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| org_id | uuid | FK → `organizations.id`, CASCADE |
| department_id | bigint | FK → `departments.id`, RESTRICT |
| candidate_profile_id | uuid | FK → `candidate_profiles.id`, SET NULL |
| it_role_id | uuid | FK → `it_roles.id`, RESTRICT, **required** |
| level_code | text | `intern` … `director`, or null |
| job_role_snapshot | text | Display text |
| session_type | text | `department`, `invitation`, `practice` |
| interaction_mode | text | `typing`, `voice`, `avatar` |
| status | text | `initiating`, `active`, `completed`, `cancelled`, `expired` |
| current_phase | text | `intro`, `experience`, `technical`, `behavioral`, `conclusion` |
| current_question_number | integer | ≥ 0, default 0 |
| total_questions | integer | 1–100 |
| scorecard_template_id | uuid | FK → `scorecard_templates.id`, SET NULL |
| invite_token | text | UQ; lean replacement for an invitation table |
| invite_expires_at | timestamptz | Optional |
| started_at / ended_at | timestamptz | `ended_at >= started_at` |
| created_at / updated_at | timestamptz | Default now() |
| final_score | numeric(5,2) | 0–10 |
| final_feedback | text | Optional |
| engine_version | text | Default `v5` |

Indexes: `idx_sessions_org`, `idx_sessions_department`, `idx_sessions_candidate`, `idx_sessions_role`, `idx_sessions_status`, `idx_sessions_started_at`, `idx_sessions_final_score`, `idx_sessions_scorecard_template`, `idx_sessions_invite_token`.

#### `interview_messages`
Full transcript.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| session_id | uuid | FK → `interview_sessions.id`, CASCADE |
| role | text | `assistant`, `user`, `system` |
| message_type | text | Required |
| content | text | Required |
| question_number | integer | ≥ 0 |
| phase | text | Optional |
| score | numeric(5,2) | 0–10 |
| follow_up_question | text | Optional |
| evaluated_at | timestamptz | Optional |
| created_at | timestamptz | Default now() |

#### `interview_evaluations`
Per-answer evaluation.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| session_id | uuid | FK → `interview_sessions.id`, CASCADE |
| message_id | uuid | FK → `interview_messages.id`, CASCADE; UQ |
| score | numeric(5,2) | 0–10 |
| technical_score | numeric(5,2) | 0–10 |
| communication_score | numeric(5,2) | 0–10 |
| strengths / weaknesses / feedback_detail | text | Optional |
| evaluated_at / created_at | timestamptz | Default now() |

### 4.7 Reasoning and evidence

#### `hypotheses`
Working hypotheses about the candidate.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| session_id | uuid | FK → `interview_sessions.id`, CASCADE |
| statement | text | Required |
| competency_id | text | FK → `competencies.id`, SET NULL |
| direction | text | `positive`, `negative` |
| confidence | numeric(5,4) | 0–1 |
| supporting_evidence | uuid[] | Evidence IDs |
| contradicting_evidence | uuid[] | Evidence IDs |
| status | text | `untested`, `testing`, `confirmed`, `refuted` |
| created_at / last_updated | timestamptz | Default now() |

#### `evidence_store`
Raw evidence extracted from answers.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| session_id | uuid | FK → `interview_sessions.id`, CASCADE |
| competency_id | text | FK → `competencies.id`, RESTRICT |
| dimension | text | One of the seven dimensions |
| score | numeric(5,2) | 0–10 |
| confidence | numeric(5,4) | 0–1 |
| evidence_text / source_question | text | Required |
| question_number | integer | ≥ 0 |
| hypothesis_id | uuid | FK → `hypotheses.id`, SET NULL |
| hypothesis_relevance | numeric(5,4) | 0–1 |
| evidence_metadata | jsonb | Default `{}` |
| created_at | timestamptz | Default now() |

Indexes: `idx_evidence_session`, `idx_evidence_session_competency`, `idx_evidence_session_dimension`, `idx_evidence_hypothesis`.

#### `interview_brain`
Authoritative live reasoning snapshot.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| session_id | uuid | FK → `interview_sessions.id`, CASCADE; UQ |
| version | integer | ≥ 1 |
| current_hypotheses / evidence_summary / competency_scores | jsonb | Required |
| difficulty_profile / decision_state | jsonb | Optional |
| brain_metadata | jsonb | Default `{}` |
| created_at / updated_at | timestamptz | Default now() |

#### `interview_timeline`
Every question, evaluation, hypothesis shift, and decision.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| session_id | uuid | FK → `interview_sessions.id`, CASCADE |
| event_type | text | Required |
| question_number | integer | Optional |
| event_data | jsonb | Default `{}` |
| created_at | timestamptz | Default now() |

### 4.8 Audit

#### `audit_log`
Append-only audit trail.

| Column | Type | Key / notes |
|---|---|---|
| id | uuid | PK |
| org_id | uuid | FK → `organizations.id`, SET NULL |
| user_id | uuid | FK → `users.id`, SET NULL |
| action | text | Required |
| resource_type / resource_id | text | Optional |
| details | jsonb | Default `{}` |
| ip_address | text | Optional |
| created_at | timestamptz | Default now() |

## 5. Relationship and cardinality map

| Parent | Child | Cardinality | Delete rule |
|---|---|---|---|
| organizations | org_users | 1 → N | CASCADE |
| organizations | org_invitations | 1 → N | CASCADE |
| organizations | departments | 1 → 1 (IT only) | CASCADE |
| organizations | scorecard_templates | 1 → N | CASCADE |
| organizations | interview_sessions | 1 → N | CASCADE |
| organizations | audit_log | 1 → N | SET NULL |
| users | org_users | 1 → N | CASCADE |
| users | org_invitations | 1 → N | CASCADE |
| users | refresh_tokens | 1 → N | CASCADE |
| users | user_password_reset_tokens | 1 → N | CASCADE |
| users | audit_log | 1 → N | SET NULL |
| departments | department_documents | 1 → N | CASCADE |
| departments | interview_templates | 1 → N | CASCADE |
| departments | interview_sessions | 1 → N | RESTRICT |
| it_roles | role_competencies | 1 → N | CASCADE |
| it_roles | interview_templates | 1 → N | RESTRICT |
| it_roles | interview_sessions | 1 → N | RESTRICT |
| competencies | role_competencies | 1 → N | CASCADE |
| competencies | hypotheses | 1 → N | SET NULL |
| competencies | evidence_store | 1 → N | RESTRICT |
| candidate_profiles | candidate_refresh_tokens | 1 → N | CASCADE |
| candidate_profiles | candidate_password_reset_tokens | 1 → N | CASCADE |
| candidate_profiles | candidate_documents | 1 → N | CASCADE |
| candidate_profiles | interview_sessions | 1 → N | SET NULL |
| scorecard_templates | interview_templates | 1 → N | SET NULL |
| scorecard_templates | interview_sessions | 1 → N | SET NULL |
| interview_sessions | interview_messages | 1 → N | CASCADE |
| interview_sessions | interview_evaluations | 1 → N | CASCADE |
| interview_sessions | hypotheses | 1 → N | CASCADE |
| interview_sessions | evidence_store | 1 → N | CASCADE |
| interview_sessions | interview_brain | 1 → 1 | CASCADE |
| interview_sessions | interview_timeline | 1 → N | CASCADE |
| interview_sessions | candidate_documents | 1 → N | SET NULL |
| interview_messages | interview_evaluations | 1 → 1 | CASCADE |
| hypotheses | evidence_store | 1 → N | SET NULL |

## 6. Enum and check values

| Field | Allowed values |
|---|---|
| `org_users.role`, `org_invitations.role` | `owner`, `member`, `viewer` |
| `org_invitations.status` | `pending`, `accepted`, `expired`, `revoked` |
| `departments.department_type` | `IT` only |
| `it_roles.family` | `software_engineering`, `frontend`, `backend`, `fullstack`, `mobile`, `game`, `embedded`, `qa`, `devops`, `cloud`, `infrastructure`, `network`, `security`, `data`, `ai_ml`, `database`, `it_support`, `architecture`, `it_management`, `business_analysis`, `design`, `erp_crm`, `technical_writing` |
| `it_roles.level_min`, `it_roles.level_max`, `interview_templates.level_code`, `interview_sessions.level_code`, `role_competencies.required_level` | `intern`, `junior`, `mid`, `senior`, `lead`, `principal`, `manager`, `director` |
| `competencies.scope` | `IT` only |
| `competencies.category` | `technical`, `behavioral`, `cognitive`, `experience`, `design`, `product`, `operations`, `general` |
| `competencies.primary_dimension`, evidence dimensions | `technical`, `communication`, `behavioral`, `reasoning`, `confidence`, `completeness`, `domain` |
| `interview_sessions.session_type` | `department`, `invitation`, `practice` |
| `interview_sessions.interaction_mode` | `typing`, `voice`, `avatar` |
| `interview_sessions.status` | `initiating`, `active`, `completed`, `cancelled`, `expired` |
| `interview_sessions.current_phase` | `intro`, `experience`, `technical`, `behavioral`, `conclusion` |
| `interview_messages.role` | `assistant`, `user`, `system` |
| `hypotheses.direction` | `positive`, `negative` |
| `hypotheses.status` | `untested`, `testing`, `confirmed`, `refuted` |

## 7. Index strategy

| Goal | Indexes |
|---|---|
| Tenant isolation | `idx_sessions_org`, `idx_audit_org` |
| Department scope | `idx_sessions_department`, `idx_interview_templates_department`, `idx_department_documents_department` |
| IT role filtering | `idx_sessions_role`, `idx_interview_templates_role`, `idx_it_roles_family` |
| Candidate lookup | `uq_candidate_profiles_email_lower`, `idx_sessions_candidate` |
| Template lookup | `idx_scorecard_templates_org`, `idx_interview_templates_scorecard` |
| Transcript reads | `idx_messages_session_question`, `idx_messages_session_created`, `idx_evaluations_session` |
| Reasoning reads | `idx_evidence_session_competency`, `idx_evidence_session_dimension`, `idx_hypotheses_session_status` |
| Timeline replay | `idx_timeline_session_created`, `idx_timeline_session_type` |
| Invite links | `idx_sessions_invite_token` (partial) |
| Audit lookup | `idx_audit_org`, `idx_audit_user`, `idx_audit_action`, `idx_audit_created` |

## 8. How to draw the ERD

Suggested canvas order (left to right):

1. **Tenancy:** `organizations`, `users`, `org_users`, `refresh_tokens`.
2. **IT department:** `departments`, `department_documents`.
3. **IT catalog:** `it_roles`, `competencies`, `role_competencies`.
4. **Candidate:** `candidate_profiles`.
5. **Templates:** `scorecard_templates`, `interview_templates`.
6. **Runtime center:** `interview_sessions`; connect `interview_messages` and `interview_evaluations`.
7. **Reasoning:** `hypotheses`, `evidence_store`, `interview_brain`, `interview_timeline`.
8. **Audit:** `audit_log`.

Color suggestion:

| Color | Domain |
|---|---|
| Purple | Organization, users, auth |
| Green | IT department and documents |
| Blue | IT catalog and reference data |
| Orange | Candidates |
| Teal | Templates |
| Red | Interview runtime and transcripts |
| Yellow | Reasoning and evidence |
| Grey | Brain, timeline, audit |

Every relationship line should show the child FK column and the delete rule (`CASCADE`, `RESTRICT`, `SET NULL`).

## 9. What is intentionally not in the lean schema

| Removed | Add later when… |
|---|---|
| Marketplace (`public_interviews`, submissions, saved listings) | Public job listings are approved as an IT-only feature |
| Scheduling (`interview_slots`, `slot_availability`, `bookings`) | Booking interviews becomes a requirement |
| Separate candidate invitation table | You need per-invite tracking beyond `interview_sessions.invite_token` |
| `candidate_sessions` | You need an explicit candidate-to-session link table in addition to `interview_sessions.candidate_profile_id` |
| `it_skills`, `it_role_skills`, `competency_skills` | Skill-level matching becomes a requirement |
| `it_role_families`, `it_role_levels` | Families/levels become user-editable data instead of checked values |
| Extra intelligence bundles (`company_brains`, `candidate_brains`, `interview_blueprints`, `scorecards`, `candidate_evidence_requirements`) | You need separately auditable snapshots per bundle |
| `scorecard_results` | You need a stored final scorecard separate from `interview_sessions` and `interview_brain` |
| `calibration_feedback` | Post-hire calibration is approved |
| `integrity_events`, `interview_events`, `v4_session_state` | Anti-cheat, event replay, or crash recovery needs durable storage |

## 10. Migration notes versus the current schema

| Current | Lean target |
|---|---|
| `departments` allows any name/type, many per org | One `departments` row per org, `department_type = 'IT'` |
| `interview_sessions.job_role` is free text | `it_role_id` FK required; `job_role_snapshot` is display only |
| `interview_templates.job_role` free text | `it_role_id` FK required |
| `candidate_invitations` table | `interview_sessions.invite_token` + `invite_expires_at` |
| `it_role_families` / `it_role_levels` tables | Checked `family`, `level_min`, `level_max` values on `it_roles` |
| `it_skills` and mappings | Removed from the lean schema |
| `scorecard_results` | Removed; final score stays on the session and brain |
| `company_brains` / `candidate_brains` / `interview_blueprints` | Removed; `interview_brain` holds the live reasoning state |
| Marketplace and scheduling tables | Removed from the lean schema |
| Calibration, integrity, event log, checkpoint tables | Removed from the lean schema |
| `candidate_documents` | Kept for uploaded resumes and parsed text |
| `org_invitations` / password reset tables | Kept because they belong to the user/org flow |

## 11. Open decisions before implementation

1. **Invite tracking.** Is `interview_sessions.invite_token` enough, or do you need a separate invitation table with send/open/accept timestamps?
2. **Resume parsing.** What must be extracted from uploaded resumes, and how long should files and extracted text be retained?
3. **Scorecard history.** Is `interview_brain.competency_scores` enough, or do you need a separate immutable `scorecard_results` row per session?
4. **Soft delete.** This schema uses hard deletes with `ON DELETE` rules. Add `deleted_at` consistently if audit retention requires it.
5. **Row-level security.** Decide whether PostgreSQL RLS is required in addition to application `org_id` filtering.
6. **Partitioning.** `interview_timeline` and `audit_log` are the first candidates at scale.

## 12. Table checklist

- [x] 6 tenancy/access tables
- [x] 2 department/document tables
- [x] 3 IT catalog tables
- [x] 4 candidate tables
- [x] 2 template tables
- [x] 3 session/transcript tables
- [x] 4 reasoning tables
- [x] 1 audit table

**Total: 25 tables.**
