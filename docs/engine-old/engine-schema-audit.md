# Engine & Schema Audit — Interview Flow (demo_autopilot)

Audit of every file and every DB table/column exercised by the interview flow
driven by `scripts/demo_autopilot.py` (org login → marketplace listing →
candidate login → session start → WS interview loop → summary → brain view).

All file usage is import-graph-verified; all column usage is traced against the
concrete code paths (`app/engine/persistence.py`, `app/services/v5_brain_persister.py`,
`app/intelligence/persist.py`, `app/services/event_log.py`,
`app/services/v4_session_store.py`, `app/repositories/*`,
`app/auth/service.py`, `app/candidates/service.py`, `app/marketplace/service.py`).

---

## 1. Engine files used by the interview flow

```
AI-Interview-Agent/
├── scripts/
│   └── demo_autopilot.py                     # driver — org login → listing → cand login → WS loop → summary → brain view
│
└── app/
    ├── main.py                               # wires every router below
    │
    ├── api/                                  # entry points
    │   ├── interview_ws.py                   # WS /ws/interview/{sid}: start_interview / submit_answer / request_question
    │   ├── interview_agent.py                # GET /interviews/{sid}/summary
    │   └── v1/
    │       ├── auth.py                       # POST /api/v1/auth/login
    │       ├── departments.py                # GET /api/v1/departments
    │       ├── candidates.py                 # /register + /login
    │       ├── marketplace.py                # listing create/list + POST .../{id}/start
    │       └── intelligence.py               # GET /api/v1/intelligence/brain/{sid}
    │
    ├── engine/                               # orchestration (all 7 files used)
    │   ├── engine.py                         # InterviewEngine: start_session / process_answer
    │   ├── lifecycle.py                      # start chain: init→planning→hypotheses→question
    │   ├── answer_processor.py               # per-turn: sanitize→evaluate→evidence
    │   ├── routing.py                        # reflection→director→difficulty→next question
    │   ├── decision.py                       # finalize: synthesis→hiring decision→report
    │   ├── persistence.py                    # DB + V5 brain snapshot writes
    │   └── builders.py                       # question / evaluation / report payloads
    │
    ├── brain/                                # V5 brain assembly (all 11 used via assembler)
    │   ├── assembler.py                      # assemble_aura_brain + refresh_brain_layers
    │   ├── calibration.py                    # calibration_state / director gate
    │   ├── candidate_memory.py               # memory snapshot
    │   ├── company_brain.py                  # company DNA
    │   ├── contradiction_detector.py         # contradiction_state
    │   ├── decision_engine.py                # 7-point decision
    │   ├── evidence_reasoner.py              # evidence_cursor / typed graph
    │   ├── hypothesis_engine.py              # initial hypotheses + uncertainty
    │   ├── question_planner.py               # question_strategy
    │   └── role_brain.py                     # role profile
    │
    ├── core/
    │   ├── interview_brain.py                # InterviewBrain (authoritative state)
    │   └── interview_state.py                # dict↔brain sync
    │
    ├── agents/
    │   ├── init/        session_init.py, company_context.py, candidate_profile.py
    │   ├── planning/    competency_planner.py, strategy_planner.py, difficulty_engine.py, action_router.py
    │   ├── evaluation/  candidate_evaluator.py, scoring.py, synthesis.py
    │   ├── reasoning/   evidence_engine.py, hypothesis_engine.py, reflection_engine.py,
    │   │                contradiction_engine.py, information_gain.py, claim_validator.py
    │   ├── generation/  question_generator.py, question_similarity_guard.py, question_memory.py
    │   └── decision/    director.py, hiring_decision.py, decision_engine.py, decision_review.py
    │
    ├── intelligence/                         # session intelligence bundle (build_intelligence=True)
    │   ├── __init__.py                       # build_interview_intelligence
    │   ├── company_cache.py                  # get_or_build_company_brain
    │   ├── company_intelligence_builder.py   # company brain
    │   ├── document_analyzer.py
    │   ├── candidate_intelligence_builder.py # candidate brain
    │   ├── candidate_matcher.py
    │   ├── resume_analyzer.py
    │   ├── interview_blueprint_builder.py
    │   ├── scorecard_resolver.py
    │   ├── role_competency_profiler.py       # build_role_context
    │   ├── persist.py                        # persist_intelligence_bundle
    │   └── _helpers.py
    │
    ├── services/
    │   ├── v4_session_store.py               # in-memory session state + Postgres checkpoint
    │   ├── v5_brain_persister.py             # InterviewBrain/EvidenceGraph/InterviewTimeline → DB
    │   ├── event_log.py                      # session events (interview_events)
    │   ├── llm_service.py                    # LLM calls
    │   ├── prompt_loader.py
    │   ├── cache.py                          # used by llm_service
    │   ├── repositories.py                   # summary endpoint
    │   ├── audit_log.py                      # listing create/update audit
    │   └── marketplace_generator.py          # rich description (listing creation only)
    │
    ├── marketplace/
    │   ├── service.py                        # start_public_interview, create_public_interview
    │   └── schemas.py
    │
    ├── candidates/
    │   ├── auth.py                           # candidate JWT (WS + summary)
    │   ├── service.py                        # register/login
    │   └── schemas.py
    │
    ├── auth/
    │   ├── jwt.py                            # token issue/decode
    │   ├── middleware.py                     # org auth
    │   ├── rbac.py                           # org role checks
    │   ├── service.py                        # login/logout/refresh
    │   ├── schemas.py
    │   ├── password.py
    │   └── google.py                         # ⚠ imported by auth.py, NOT exercised (autopilot uses email/pass)
    │
    ├── repositories/
    │   ├── session_repository.py, message_repository.py, evaluation_repository.py,
    │   ├── evidence_repository.py, base_repository.py
    │
    ├── data/
    │   ├── competency_resolver.py            # taxonomy resolution
    │   ├── competency_taxonomy.py            # COMPETENCY_TAXONOMY / skill map
    │   └── competency_graph.py               # graph edges (assembler)
    │
    ├── config/
    │   ├── interview_styles.py               # AURA style
    │   └── settings.py
    │
    ├── database/
    │   ├── session.py, deps.py, base.py
    │
    ├── models/
    │   ├── db.py                             # InterviewSession, InterviewBrain, EvidenceGraph, InterviewTimeline, …
    │   └── llm.py                            # llm service backend
    │
    └── utils/
        └── input_sanitizer.py                # answer sanitization
```

Not part of the flow (excluded): all other routers in `app/api/v1/`
(`analytics`, `scheduling`, `admin`, `invitations`, `public`, `scorecards`,
`candidate_ranking`, `audit_logs`, `demo`, `orgs`), `app/agents` files not
listed, `app/services/email.py`, `app/candidates/resume_service.py` (imported
at module load only, never called by the autopilot), `app/auth/google.py`
(imported, unused in this flow).

Note: `app/api/v1/intelligence.py` imports `build_interview_intelligence` /
`persist_intelligence_bundle` at the top but only `GET /brain/{sid}` runs in
this flow — the bundle build actually fires from `app/engine/lifecycle.py`.

---

## 2. Database tables & columns used by the interview flow

### Tier A — V5 reasoning core (written every turn / at finalize)

| Table | Columns used | Columns NOT used | Benefit to interview flow |
|---|---|---|---|
| **interview_brain** | `session_id`, `version`, `current_hypotheses`, `evidence_summary`, `competency_scores`, `difficulty_profile`, `decision_state`, `brain_metadata`, `created_at`, `updated_at` | — (all used) | Authoritative durable brain snapshot each turn; powers `/summary` and `/intelligence/brain/{sid}` |
| **evidence_graph** | `session_id`, `nodes`, `edges`, `version`, `created_at`, `updated_at` | — (all used) | Persisted evidence→hypothesis/competency graph (`brain_view.json` source) |
| **interview_timeline** | `session_id`, `event_type`, `question_number`, `event_data`, `created_at` | — (all used) | `brain_snapshot` replay; drives frontend graph animation |
| **hypotheses** | `id`, `session_id`, `statement`, `competency`, `direction`, `confidence`, `supporting_evidence`, `contradicting_evidence`, `status`, `last_updated` | `created_at` (default only) | Hypothesis ledger the director probes against |
| **interview_objectives** | `id`, `session_id`, `competency`, `dimension`, `hypothesis_id`, `hypothesis_statement`, `hypothesis_confidence`, `status`, `evidence_ids`, `priority` | `created_at` (default only) | Tracks probe→satisfied lifecycle per question |
| **observations** | `session_id`, `question_number`, `type`, `value`, `evidence`, `pattern`, `risk_signal`, `created_at` | — (all used) | Behavioral risk signals (hedging, latency, certainty shifts) |
| **consistency_checks** | `session_id`, `dimension`, `answers_compared`, `consistency_score`, `contradictions`, `check_type`, `assessment`, `score`, `confidence`, `evidence`, `checked_at` | `created_at` (default only) | Cross-answer consistency validation at finalize |
| **scorecard_results** | `session_id`, `scores`, `weighted_score` | `template_id` | Final per-competency scorecard |
| **v4_session_state** | `session_id`, `state`, `state_version`, `updated_at` | — (all used) | Durable checkpoint of live engine state (crash recovery) |
| **interview_events** | `session_id`, `seq`, `event_type`, `payload`, `created_at` | `id` (sequence default) | Append-only event log (start/selection/evaluation events) |

### Tier B — Transcript tables (per answered turn + summary read)

| Table | Columns used | Columns NOT used | Benefit |
|---|---|---|---|
| **interview_sessions** | `id`, `org_id`, `department_id`, `candidate_profile_id`, `job_role`, `session_type`, `interaction_mode`, `status`, `current_phase`, `current_question_number`, `total_questions`, `scorecard_template_id`, `started_at`, `created_at`, `updated_at`, `final_score`, `final_feedback`, `ended_at`, `engine_version` | — (all used) | The session anchor + completion state |
| **interview_messages** | `id`, `session_id`, `role`, `message_type`, `content`, `question_number`, `phase`, `score`, `created_at` | `follow_up_question`, `evaluated_at` | Full Q/A transcript for summary/report |
| **interview_evaluations** | `id`, `session_id`, `message_id`, `score`, `technical_score`, `communication_score`, `strengths`, `weaknesses`, `created_at` | `feedback_detail` (always NULL in flow), `evaluated_at` (default only) | Per-answer scores + strengths/weaknesses |
| **evidence_store** | `id`, `session_id`, `competency`, `dimension`, `score`, `confidence`, `evidence_text`, `source_question`, `question_number`, `hypothesis_id`, `hypothesis_relevance`, `evidence_metadata`, `created_at` | — (all used) | Raw claim evidence feeding the brain |

### Tier C — Intelligence bundle (written once at session start)

| Table | Columns used | Columns NOT used | Benefit |
|---|---|---|---|
| **company_brains** | `session_id`, `department_id`, `company_name`, `industry`, `company_vision`, `values`, `technical_stack`, `culture`, `success_signals`, `red_flags`, `source_documents`, `snapshot` | `source_version` (default only) | Company DNA steering question tone/topics |
| **interview_blueprints** | `session_id`, `department_id`, `role`, `objectives`, `phases`, `hypothesis_template`, `evidence_requirements`, `snapshot` | — (all used) | Role plan → evidence requirements |
| **candidate_brains** | `session_id`, `candidate_id`, `full_name`, `resume_summary`, `skills`, `strengths`, `weaknesses`, `work_history`, `inferred_seniority`, `persona`, `snapshot` | — (all used) | Initial hypotheses from resume/profile |
| **scorecards** | `session_id`, `department_id`, `role`, `competencies`, `required_level`, `snapshot` | — (all used) | Scorecard taxonomy for competency resolution |
| **candidate_evidence_requirements** | `session_id`, `competency`, `dimension`, `required_probes`, `evidence_level`, `snapshot` | — (all used) | Min-evidence gates per competency |

### Tier D — Auth / org / listing (mostly reads in demo, some writes)

| Table | Columns used | Columns NOT used | Benefit |
|---|---|---|---|
| **users** | `id`, `email`, `password_hash`, `name`, `is_active` (read), `created_at` | `avatar_url`, `is_admin` | Org login (seeded, not created in flow) |
| **organizations** | `id`, `name`, `slug` | `logo_url`, `description`, `website`, `settings`, `is_active` | Org resolution for role context |
| **org_users** | `id`, `org_id`, `user_id`, `role` | `invited_by`, `joined_at` | Login memberships (role = owner) |
| **refresh_tokens** | `id`, `user_id`, `token_hash`, `expires_at` | `revoked` (only on refresh/logout), `created_at` | Org token session |
| **departments** | `id`, `org_id`, `name` | `website`, `description`, `created_at` | Role/company context for the interview |
| **candidate_profiles** | `id`, `email`, `name`, `password_hash`, `is_registered`, `is_verified`, `skills`, `profile_data`, `created_at`, `updated_at` | `phone`, `resume_url`, `google_id`, `verified_at`, `verification_token_hash`, `verification_sent_at` | Candidate auth + resume/profile → hypotheses |
| **candidate_refresh_tokens** | `id`, `candidate_id`, `token_hash`, `expires_at`, `revoked`, `created_at` | — | Candidate token rotation |
| **candidate_sessions** | `id`, `candidate_id`, `session_id`, `created_at` | — | Practice-session linking |
| **public_interviews** | `id`, `org_id`, `department_id`, `title`, `description`, `interview_mode`, `is_open`, `max_candidates`, `skills_required`, `rich_description`, `style_name`, `created_at` | `template_id`, `verification_method`, `token`, `token_expires_at`, `starts_at`, `expires_at` | The marketplace listing being interviewed against |
| **public_interview_submissions** | `id`, `public_id`, `session_id`, `candidate_email`, `candidate_name`, `started_at` | `completed_at`, `created_at` | Tracks candidate ↔ listing start |
| **audit_log** | `org_id`, `user_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `created_at` | `details` | Listing create/update audit trail |

### Tier E — NOT touched by this flow

`alembic_version` (migration bookkeeping) · `interview_slots`, `slot_availability`,
`bookings` (scheduling) · `candidate_invitations` (email invite flow) ·
`candidate_saved_listings` (no save in demo) · `org_invitations`,
`user_password_reset_tokens`, `candidate_password_reset_tokens` (invite/password
flows) · `interview_templates` (FK target only, no rows used) ·
`scorecard_templates` (FK target only) · `candidate_documents` (needs a resume
upload) · `department_documents` (only read by the Pinecone RAG retriever when a
department has docs — skipped with no docs).

---

## 3. Audit caveats

- `public_interviews` / `audit_log` / `rich_description` only write in the
  "create new listing" branch of the autopilot; if a listing already exists it
  is reused (read-only).
- `department_documents` is conditionally read via `app/rag/pinecone_store` →
  `get_department_retriever` inside `app/intelligence/company_intelligence_builder.py`,
  only when `department_id` is set and documents exist.
- All persistence is best-effort by design — a DB failure never breaks an
  interview (`app/engine/persistence.py` docstring).
