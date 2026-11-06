# 05 — File map of the engine

> Last updated: 2026-08-09 · Tag: [AURA-1.6][evidence-reading]
> Every file below is used by the interview flow (import-graph verified at audit time).

## Driver

| File | Role |
|---|---|
| `scripts/demo_autopilot.py` | Headless driver: org login → departments → marketplace listing → candidate login → session start → WS loop → summary → brain view |

## Entry points

| File | Key symbols |
|---|---|
| `app/main.py` | Wires all routers (`app.include_router(...)` at :95-114) |
| `app/api/interview_ws.py` | `interview_websocket` (:297) — WS dispatcher |
| `app/api/interview_agent.py` | `GET /interviews/{sid}/summary` |
| `app/api/v1/auth.py` | org login |
| `app/api/v1/departments.py` | departments list |
| `app/api/v1/candidates.py` | register / login / me |
| `app/api/v1/marketplace.py` | listing CRUD + `start_interview` (:55) |
| `app/api/v1/intelligence.py` | `get_brain` (:124) — `GET /intelligence/brain/{sid}` |
| `app/api/v1/candidate_ranking.py` | `get_candidate_ranking`, `build_ranking_row`, `annotate_comparability`, `sort_rankings` — calibrated + comparable `/candidates/ranking` (T4) |
| `app/api/v1/calibration.py` | `record_feedback`, `get_drift_report`, `get_drift_summary` — T4 calibration loop (`/orgs/{org_id}/calibration/*`) |

## Engine core

| File | Key symbols |
|---|---|
| `app/engine/engine.py` | `InterviewEngine` (:28) — `start_session` (:50), `process_answer` (:69), `get_brain` (:82) |
| `app/engine/lifecycle.py` | `start_session` (:24), `INTELLIGENCE_KEYS` (:13) |
| `app/engine/answer_processor.py` | `process_answer` (:17) |
| `app/engine/routing.py` | `route_answer` (:314) |
| `app/engine/decision.py` | `finalize_session` (:44) |
| `app/engine/persistence.py` | `persist_evidence`, `persist_v5_snapshot`, best-effort writes |
| `app/engine/builders.py` | `build_start_response`, `build_state_response`, question/eval/report payloads |
| `app/core/interview_brain.py` | `InterviewBrain` — authoritative session state |
| `app/core/interview_state.py` | `brain_to_dict`, `dict_to_brain`, `sync_brain` |

## Brain layers (V5 deterministic)

| File | Key symbols |
|---|---|
| `app/brain/assembler.py` | `assemble_aura_brain`, `refresh_brain_layers` |
| `app/brain/role_brain.py` | `build_role_brain` (:135), `classify_seniority` (:103), `default_probe_for` (:211) |
| `app/brain/company_brain.py` | company DNA layer |
| `app/brain/hypothesis_engine.py` | `collect_evidence_for_hypothesis`, `missing_evidence_for` (:36), `hypothesis_uncertainty` (:69), `build_hypothesis_brain`, `uncertainty_map` (:132) |
| `app/brain/evidence_reasoner.py` | `evidence_summary_stats` (:113), evidence cursor — accepts the `evidence_reading` (13th layer) and applies the downgrade-only rule via `classify_claim` (:77) |
| `app/brain/calibration.py` | `calibration_state` / director gate |
| `app/brain/candidate_memory.py` | memory snapshot |
| `app/brain/contradiction_detector.py` | `contradiction_state` |
| `app/brain/decision_engine.py` | 7-point decision layer |
| `app/brain/question_planner.py` | `question_strategy` |

## Agents (nodes)

| File | Key symbols |
|---|---|
| `app/agents/init/session_init.py` | `session_init_node` |
| `app/agents/init/company_context.py` | `department_context_node` |
| `app/agents/init/candidate_profile.py` | `candidate_profile_node` |
| `app/agents/planning/competency_planner.py` | `competency_planner_node` |
| `app/agents/planning/strategy_planner.py` | `strategy_brain_node` |
| `app/agents/planning/difficulty_engine.py` | `difficulty_governor` (:203), `role_difficulty_floor` (:150) |
| `app/agents/planning/action_router.py` | action director |
| `app/agents/evaluation/candidate_evaluator.py` | `unified_evaluator_node` (:40), `_unified_evaluator` (:55) — **family-aware** (T2): emits only `active_dimensions`, resolves `primary_dimension` + `domain_label` per family, renders `{{rubric}}` |
| `app/agents/evaluation/scoring.py` | `reconcile_composite` (:88), `explainable_scoring_node` (:269), `_apply_evaluator_calibration` (:201), `DEFAULT_DIMENSION_WEIGHTS` (:42) — composite weights resolve per family via `dimension_weights(category)` |
| `app/agents/evaluation/synthesis.py` | final synthesis |
| `app/agents/evaluation/evidence_reading.py` | `evidence_reading_node` (:23) — best-effort semantic read of the raw answers at finalization; LLM failure degrades to the deterministic path |
| `app/agents/reasoning/evidence_engine.py` | `evidence_extractor_node`, `_normalize_competency_alias` |
| `app/agents/reasoning/evidence_reading.py` | `effective_claim` (:56) — **downgrade-only** semantic override, `map_evidence_reading` (:68), `evidence_reading_risk_flags` (:124), `evidence_reading_checks` (:149), `transcript_payload` (:185) — deterministic core of the 13th brain layer |
| `app/agents/reasoning/hypothesis_engine.py` | `hypothesis_node` (:582), `update_hypotheses`, `_seed_hypothesis_for_competency` |
| `app/agents/reasoning/reflection_engine.py` | reflection |
| `app/agents/reasoning/contradiction_engine.py` | `evaluate_sufficiency` (:251), `compute_canonical_score` (:176), `_HIGH_PRIORITY_IDS` (:19) |
| `app/agents/reasoning/information_gain.py` | next-target scoring |
| `app/agents/reasoning/claim_validator.py` | claim verification |
| `app/agents/generation/question_generator.py` | `question_generator_node` |
| `app/agents/generation/question_similarity_guard.py` | duplicate avoidance |
| `app/agents/generation/question_memory.py` | question memory |
| `app/agents/decision/director.py` | action director |
| `app/agents/decision/hiring_decision.py` | hiring-decision node |
| `app/agents/decision/decision_engine.py` | `compute_decision_score` (:77), `decide_hiring_decision` (:132), `map_decision` (:114) |
| `app/agents/decision/decision_review.py` | `review_decision` (:83), `finalize_decision` (:164), `decision_review_node` (:205) |

## Intelligence (V5 bundles)

| File | Key symbols |
|---|---|
| `app/intelligence/__init__.py` | `build_interview_intelligence` |
| `app/intelligence/role_competency_profiler.py` | `build_role_context` (:53), `suggest_competencies` (:217), `_suggest_from_taxonomy` (:172), `_normalize_entry` (:95), `_validate_suggestions` (:149) |
| `app/intelligence/company_cache.py` | `get_or_build_company_brain` |
| `app/intelligence/company_intelligence_builder.py` | company brain |
| `app/intelligence/document_analyzer.py` | doc → company brain |
| `app/intelligence/candidate_intelligence_builder.py` | candidate brain |
| `app/intelligence/candidate_matcher.py` | profile matching |
| `app/intelligence/resume_analyzer.py` | resume analysis — two optional LLM backends behind `RESUME_LLM_BACKEND` (`dspy` default / `legacy`); `_use_dspy_backend()` switch, `_legacy_llm_parse()` |
| `app/intelligence/dspy_modules.py` | DSPy pilot — `ResumeAnalysis` signature, `ResumeAnalyzerProgram` (`forward`/`aforward`), `run_resume_analysis` → dict; `restrict_pickle=True` cache |
| `app/intelligence/interview_blueprint_builder.py` | blueprint |
| `app/intelligence/scorecard_resolver.py` | scorecard competencies |
| `app/intelligence/persist.py` | `persist_intelligence_bundle` |
| `app/intelligence/_helpers.py` | JSON parsing helpers |

## Services & data

| File | Key symbols |
|---|---|
| `app/services/v4_session_store.py` | in-memory session store + Postgres checkpoint |
| `app/services/v5_brain_persister.py` | brain/evidence graph/timeline → DB |
| `app/services/calibration_service.py` | **T4 drift math** (pure) — `classify_prediction`, `difficulty_credit`/`difficulty_band`, `build_drift_report`, `build_drift_summary`, insight generation |
| `app/services/event_log.py` | session events |
| `app/services/llm_service.py` | LLM calls |
| `app/services/prompt_loader.py` | `PromptLoader` / `load_prompt` |
| `app/services/repositories.py` | summary reads |
| `app/marketplace/service.py` | `start_public_interview`, `create_public_interview` |
| `app/candidates/service.py` | register/login |
| `app/auth/*` | jwt, middleware, rbac, service, password |
| `app/repositories/*` | session/message/evaluation/evidence repositories |
| `app/data/competency_resolver.py` | `resolve_competencies` (:344), `default_taxonomy` (:69), `derive_required_competencies` (:146), `_FALLBACK_WEIGHTS` (:60) |
| `app/data/competency_taxonomy.py` | `COMPETENCY_TAXONOMY`, `SKILL_TO_COMPETENCY` |
| `app/data/competency_graph.py` | `COMPETENCY_CHILDREN` (:30), `taxonomy_to_graph` (:193) |
| `app/data/rubrics.py` | **T2 family rubrics** — `dimension_weights` (:288), `active_dimensions` (:313), `render_rubric` (:358), `evidence_keywords` (:333), `anchors` (:347), `domain_label_for` (:373) — single source of truth for the deterministic composite + evaluator prompt (tests: `tests/unit/data/test_rubrics.py`) |
| `app/config/interview_styles.py` | AURA style |
| `app/models/db.py` | all SQLAlchemy models |
| `app/utils/input_sanitizer.py` | answer sanitization + prompt-injection scan |

## Not part of the flow (excluded)

Other routers (`analytics`, `scheduling`, `admin`, `invitations`, `public`,
`scorecards`, `audit_logs`, `demo`, `orgs`), `app/services/email.py`,
`app/candidates/resume_service.py`, `app/auth/google.py` (imported at module
load, not exercised), RAG service except the company-builder retrieval branch.
(`candidate_ranking` and `calibration` are org-side endpoints documented in
03-apis.md; they are not part of the interview flow itself.)
