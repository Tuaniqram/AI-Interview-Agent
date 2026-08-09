# AURA Engine — Changelog

> Append-only ledger. Every accepted, tested change gets a tagged entry.
> Tag convention: `[AURA-x.y][feature-tag]`.

## [AURA-1.0-baseline] — 2026-08-09
- **Baseline documentation**: created `docs/aura/` — API surface, DB schema,
  file map, prompt inventory, interview flow, reasoning core, decision engine,
  knowledge bases.
- **Test scaffold**: created `tests/` with `unit/`, `contract/`, `integration/`
  (DB-optional, self-skipping via `skipif`), `e2e/` (opt-in). `pytest.ini`
  registers the `unit`/`contract`/`integration`/`db`/`llm`/`e2e` markers and
  defaults to the fast set (`-m "not integration and not e2e and not llm"`).
  Full default run is green (408 pre-existing + 41 new) with zero external
  services.
- **Baseline unit/contract tests** (new, `tests/unit/`, `tests/contract/`):
  - taxonomy-integrity **canary** — every id referenced by the graph, role
    brain, resolver and skill map exists in `COMPETENCY_TAXONOMY`, with a
    documented allowance for the four known tech orphans T1 will re-add;
  - role-brain determinism — `classify_seniority`, `detect_role_class`,
    `build_role_brain` shapes/importance band/probe coverage;
  - data contracts — `default_taxonomy` weights, graph coverage,
    `taxonomy_to_graph` required/stub semantics, `map_skill_to_competency`.
  - The pre-existing root suite (408 tests) already locks the deterministic
    behavior of `suggest_competencies(use_llm=False)`, `compute_canonical_score`,
    `compute_decision_score`, `missing_evidence_for`, and the resolvers.

---

## [AURA-1.1][T1-taxonomy] — 2026-08-09
- **Taxonomy expansion** (`app/data/competency_taxonomy.py`): re-added the four
  orphaned tech competencies (`tech_event_driven`, `tech_deployment`,
  `tech_caching`, `tech_data_modeling` — graph children already existed) and
  added 8 job families × 5 competencies each: `com_` commerce, `mkt_` marketing,
  `des_` design, `prd_` product, `hr_` HR, `fin_` finance, `ops_` operations,
  `cs_` customer success (65 competencies / 12 categories total). Family
  competencies lead with the `domain` evidence dimension.
- **Skill map**: `SKILL_TO_COMPETENCY` extended for family skills (seo, roadmap,
  churn, negotiation, …); `kafka` now maps to `tech_event_driven`.
- **Profiler unblock** (`role_competency_profiler.py`): `_CATEGORY_PREFIXES` and
  `_CATEGORIES` accept the 8 new families; `detect_family` resolves role
  title/description onto a family and `_suggest_from_taxonomy` pads with
  family-specific anchors instead of always tech ones — a Marketing Manager with
  no declared skills still gets marketing competencies offline.
- **Resolver** (`competency_resolver.py`): `DEFAULT_DIMENSIONS_BY_CATEGORY`
  covers the 8 families; `_FALLBACK_WEIGHTS` adds family + re-added-tech anchors.
- **Role brain** (`role_brain.py`): 8 new role classes (sales, marketing,
  design, product, hr, finance, operations, customer_success), family category
  importance bases, canonical importance for 25 family anchors, and 22 new
  must-prove probes.
- **Prompt** (`prompts/intelligence/role_competency_profiler.md`): documents the
  12 prefixes/categories and the `domain`-first dimension rule.
- **Tests**: family taxonomy invariants, deterministic family-aware profiler
  (all 8 families, offline), LLM-validation acceptance of family ids, role-brain
  family detection/importance/probes, non-tech `derive_domain_label`.

## [AURA-1.2][T2-scoring] — 2026-08-09
- **Family rubrics** (`app/data/rubrics.py`): the single source of truth for
  deterministic scoring and evaluator prompt rendering. 7 dimensions
  (`technical`, `domain`, `communication`, `reasoning`, `behavioral`,
  `confidence`, `completeness`) with per-dimension band anchors. Family
  resolution: the tech rubric scores `technical` highest; every non-tech family
  (commerce, marketing, design, product, HR, finance, operations, customer
  success) weights `domain` highest and zeroes `technical` so the composite is
  never inflated by a dimension the role does not exercise. `dimension_weights`
  also encodes the role's importance weighting for the composite.
- **Active-dimension evaluator** (`candidate_evaluator.py`): the unified
  evaluator now emits only the dimensions a family actually scores
  (`active_dimensions`), with `primary_dimension` = the family's top-weighted
  dimension, and renders the family rubric block (`render_rubric`) plus
  family-resolved domain label into the prompt.
- **Prompt** (`prompts/evaluation/unified_evaluator.md`): documents the
  family rubric contract — new `{{rubric}}`, `{{primary_dimension}}` variables
  and family-resolved `{{domain_label}}`.
- **Deterministic composite** (`scoring.py`): `reconcile_composite` resolves
  weights via `dimension_weights(category)` (importance-weighted, family-aware)
  instead of a fixed technical default; `explainable_scoring_node` stays
  deterministic and backward compatible with the V4/V5 decision layers.
- **Family-aware calibration** (`_apply_evaluator_calibration`, F6): evidence
  keyword sets are keyed by family (`evidence_keywords`); calibration
  sign-bounds scores only on dimensions the family actually scores.
- **Note**: the seniority-floor difficulty credit (`role_difficulty_floor`,
  director-gate `role_difficulty_floor` clamp, `calibrated_quality`, D2 in
  `compute_decision_score`, `floor_satisfied`) shipped in the earlier brain
  layers and remains unchanged; T2 scoring integrates with, and does not
  duplicate, it.
- **Tests** (`tests/unit/data/test_rubrics.py` and scoring tests): rubric
  structure per family, weight normalization, tech-vs-family dimension
  selection, anchor rendering, family-aware composite recomputation,
  calibration keyword sets.

## [AURA-1.3][T4-calibration-ranking] — 2026-08-09
- **Calibration loop — measure + report drift** (`app/api/v1/calibration.py`,
  `app/services/calibration_service.py`): deterministic, no LLM, no auto-tuning.
  - New table `calibration_feedback` (migration `b1a2c3d4e5f6`): one row per
    session holding the recruiter's actual post-hire outcome plus a snapshot of
    the session's predicted verdict/score and difficulty/floor. The predicted
    side is sourced from the already-persisted
    `interview_brain.brain_metadata.calibration_state` — nothing new is
    recomputed or written at finalize.
  - `PUT /orgs/{org_id}/calibration/feedback/{session_id}` — record
    `actual_outcome` (strong_performance / met_expectations /
    below_expectations / terminated_during_probation / no_feedback) against a
    completed session (404/400 guarded).
  - `GET .../calibration/drift` — predicted-vs-actual reconciliation: coarse
    verdict buckets (hire / lean_hire / no_hire / uncertain), correctness rate,
    over/under-prediction counts, bucketed by job family (`detect_family`) and
    difficulty-credit band (credit mirrors `app/brain/calibration.py`), plus
    deterministic insight strings (structural over/under-prediction, band and
    family over-prediction).
  - `GET .../calibration/drift/summary` — headline numbers incl. awaiting feedback.
- **Cross-candidate ranking — calibrated + comparable**
  (`app/api/v1/candidate_ranking.py`): `/ranking` rows now carry
  `calibrated_score`, `difficulty_reached`, `role_floor`, `family`
  (`detect_family`), `score_band`, and a `comparable_note` when a candidate's
  family differs from the cohort's dominant family (calibrated scores are only
  directly comparable within a family cohort). New `sort_by=final|calibrated`
  (nulls last) and `family` filter. Sessions without a persisted
  `calibration_state` fall back to `calibrated_score: null` (sorted last).
  `/ranking/summary` and `/export` stay backward compatible.
- **Migration**: `alembic/versions/b1a2c3d4e5f6_add_calibration_feedback.py`.
- **Tests**: drift math (bucket mapping, over/under/uncertain classification,
  difficulty-credit bands, insight generation, summary counts) in
  `tests/unit/services/test_calibration_service.py`; API contract tests
  (feedback record/update/404/400/422, drift + summary shapes) in
  `tests/test_calibration_api.py`; ranking helpers (family detection,
  calibration fallback, score bands, comparability notes, both sort orders) in
  `tests/unit/ranking/test_candidate_ranking.py`.

## [AURA-1.4][docs-versioning] — 2026-08-09
- **Docs + tests are now versioned**: `.gitignore` no longer excludes `docs/`
  and `tests/` (previously untracked working artifacts). The Wave 1-3
  documentation, `WAVE-PLAN.md`, and the full test suite (565 passing) are
  committed with the code in `2bb9e07`.
- **`WAVE-PLAN.md`** added to `docs/aura/` and linked from the README index —
  tracks T1-taxonomy / T2-scoring / T4-calibration-ranking completion status.
- **`BRAIN_VIEW.md`** added to `docs/aura/` — schema + change ledger for the
  `brain_view.json` output (T2 → value changes for new sessions only; T4 →
  no change).
- **Verification**: `python -m pytest -q` → 565 passed (526 pre-existing + 39
  new for T2/T4), zero external services; `alembic heads` resolves to the
  calibration-feedback migration.

## [AURA-1.5][brain-view-consistency] — 2026-08-09
- **Root-caused the `brain_view.json` inconsistencies** found in the 2026-08-07
  capture (session `d0e0b2e7`):
  - `unanswered_hypotheses` 1 vs 2 — `finalize_session` refreshed only
    `hiring_recommendation` from the post-update hypothesis state while
    `evidence_sufficiency` kept the last reflection frame's pre-update value;
    both are persisted side-by-side in `decision_state`.
  - `gap`/coverage surfaces disagreed — `competency_summary`→`evidence_summary`
    only contained competencies that collected evidence, silently dropping
    zero-evidence required competencies that `evidence_sufficiency.details`
    still listed with `gap=1.0`.
  - `calibrated_score` lived only under `hiring_decision`, never next to the
    raw `hiring_recommendation`.
- **`refresh_sufficiency_and_recommendation`** (`app/engine/builders.py`):
  recomputes `evidence_sufficiency` + `hiring_recommendation` from the same
  snapshot; `finalize_session` (`app/engine/decision.py`) refreshes both, so
  the persisted pair can never disagree again.
- **Persister backfill** (`app/services/v5_brain_persister.py`:
  `_backfill_evidence_summary`): `interview_brain.evidence_summary` now unions
  every required competency — zero-evidence ones appear with `gap=1.0`,
  `evidence_count=0`, matching `evidence_sufficiency.details`. Pure
  serialization change; live `competency_summary`/scorecard rows untouched.
- **T2/T4 surfaced in the final recommendation** (`app/engine/decision.py`):
  `hiring_recommendation` gains `dimension_scores` (per-required-competency
  average/evidence_count/gap/covered), `family` (competency → taxonomy family),
  and — when the T4 calibration override fires — `calibrated_verdict` /
  `calibrated_score` / `calibration_source` mirrored from `hiring_decision`.
  `confidence_v2` (blended, calibration-preferred) was confirmed deliberate and
  documented in `BRAIN_VIEW.md`.
- **Tests**: 6 new regression tests — refresh consistency (sufficiency ≡
  recommendation `unanswered_hypotheses`), error fallback, dimension_scores +
  family enrichment, calibration mirroring, and persister backfill (unit +
  snapshot). Suite now 571 passed / 1 deselected.
- **`demo_autopilot.py`** (`scripts/`): new `--verify` flag runs integrity
  checks on the finished session and exits non-zero on failure — V5 brain
  layers present on every evaluation frame, monotonic evidence totals,
  single-source verdict across WS report → `/summary` → `/brain`, and the
  AURA-1.5 brain_view invariants (unanswered agreement, complete
  evidence_summary/dimension_scores, zero-evidence gap=1.0, family coverage,
  calibrated result surfaced). New `--calibration-feedback {outcome}` flag
  runs the T4 round-trip: `PUT /calibration/feedback/{sid}` → `GET
  /calibration/drift` + `/drift/summary` → `GET /candidates/ranking?sort_by=calibrated`.
- **`BRAIN_VIEW.md`** ledger updated with AURA-1.5 (value changes for new
  sessions + additive keys).
- **Demo brains regenerated** (`out/brain_senior_backend_engineer.json`,
  `out/brain_senior_frontend_engineer.json`): the 2026-07-08 files referenced
  legacy competency ids (`tech_aws_deployment`, `tech_fastapi_sqlalchemy`) that
  no longer exist in `COMPETENCY_TAXONOMY` and showed
  `difficulty_state.floor_satisfied=false` with `difficulty_reached=1` below the
  senior floor. Seeded the Nova listings (`scripts/setup_role_demo.py`) and
  rebuilt via `scripts/build_brain_demo.py --out-dir out` (deterministic path):
  critical competencies now use current ids (`tech_db`, `tech_event_driven`,
  `tech_data_modeling`, `tech_security`, …), `floor_satisfied=true`, and the
  two role brains differ (Jaccard overlap 0.09).

## [AURA-1.5][brain-view-consistency] — 2026-08-09 (round 2)
- **`dimension_scores` union fix** (`app/engine/decision.py`
  `_enrich_recommendation`): the final `hiring_recommendation.dimension_scores`
  now covers the **union** of required competencies + any competency that
  collected evidence, so its key set exactly equals
  `interview_brain.evidence_summary`. The `--verify` check
  `evidence_summary_complete` caught competencies probed beyond the plan
  (`tech_core`, `behav_communication`) missing from `dimension_scores` while
  present in `evidence_summary`. New regression test
  `test_dimension_scores_cover_evidenced_but_unrequired_competencies`.
- **`decision_state.hiring_decision` persistence** (`app/services/v5_brain_persister.py`):
  the deterministic final decision is now stored in `decision_state`, surfacing
  the single source of truth for the verdict in the brain view. Previously
  `decision_state` only carried `hiring_recommendation`, so the `--verify` check
  `brain_decision_matches_report` always read `None`. Persister test now asserts
  `decision_state.hiring_decision` round-trips.
- **`demo_autopilot.py` org-token refresh**: the org access token minted at
  login can expire during a long interview; the T4 calibration round-trip now
  re-logs-in the org before `PUT /calibration/feedback/{sid}` (same pattern as
  the existing candidate re-login).
- **Live end-to-end run**: `demo_autopilot.py --verify --calibration-feedback
  met_expectations` against the Nova backend (session
  `6636e6ce-b92d-457b-b990-1b3c16c9191a`, verdict `hire`): **VERIFY OK (all
  checks passed)** — including `brain_decision_matches_report`,
  `evidence_summary_complete` and (this session hit a calibration override)
  `calibrated_surfaced`. T4 round-trip recorded `met_expectations`; drift
  correctly flags the over-predictions (predicted `hire` vs calibrated
  `6.5`/`lean_hire`). Captures committed:
  `docs/aura/output/brain_view_v1.json` (pre-fix reference, session
  `d0e0b2e7`), `docs/aura/output/brain_view_v2.json` + `summary.json` (post-fix
  session `6636e6ce`), and the run log
  `docs/aura/output-demo/demo.log`.

## [AURA-1.6][evidence-reading] — 2026-08-09
- **Evidence Reading V5 — semantic read of the raw answers** (the 13th brain
  layer). LLM produces signals, deterministic engine applies them:
  - `app/agents/reasoning/evidence_reading.py` (deterministic core):
    `effective_claim` is the **downgrade-only** override —
    `min(semantic, regex)` over mentioned < demonstrated < proven — so the LLM
    can only confirm or downgrade a claim, never inflate it past what the
    deterministic (regex) signals already support. `map_evidence_reading`
    normalizes the LLM output (drops hallucinated ids / invalid enums),
    `evidence_reading_risk_flags` / `evidence_reading_checks` derive additive
    risk flags and review checks (severity capped at `medium`), and
    `transcript_payload` size-caps the transcript sent to the model.
  - `app/agents/evaluation/evidence_reading.py` (`evidence_reading_node`):
    best-effort async node run at finalization — builds the transcript, invokes
    the LLM with `prompts/evaluation/evidence_reading.md`, maps the response
    onto `state["evidence_reading"]`. Any failure degrades to the current
    deterministic path (state returned unchanged); empty evidence skips.
  - `app/brain/evidence_reasoner.py`: `classify_claim` / `evidence_summary_stats`
    accept the reading and apply the downgrade-only rule per record, so
    `calibration_state.proof_ratio` and the decision layers reflect semantic
    corrections deterministically.
  - `app/brain/decision_engine.py` + `app/agents/decision/decision_review.py`:
    the reading's flags feed `decision_state.risk_flags` and the semantic
    review checks (`off_rubric_flag`, `cross_answer_risk`,
    `unverifiable_claims`) — additive only, capped at `medium`, so they flag
    for review and trim confidence but never demote a decisive verdict.
  - `app/brain/assembler.py`: `evidence_reading` is the **13th layer**
    (`_LAYER_NAMES`), with a utilization status in the brain view.
  - `app/engine/decision.py` runs the node in `finalize_session`;
    `app/engine/builders.py` adds a compact `evidence_reading` summary to the
    report; `app/api/v1/intelligence.py` surfaces the layer in the brain view
    **additive-only** (absent on sessions without a reading).
- **Prompt** (`prompts/evaluation/evidence_reading.md`): instructs the model to
  read — never score, never decide — with a strict JSON schema
  (`per_answer` / `off_rubric` / `semantic_risks`) and a hallucinated-id ban.
- **Tests**: `tests/test_evidence_reading.py` (12) — downgrade-only rule,
  regex-proven → semantic downgrade, corroboration, mapper normalization + id
  dropping, risk flags/checks capped at medium, transcript cap, node
  populate/fallback/skip, decision-review flag-but-never-demote. Extended
  `tests/test_brain_assembler.py` (13-layer shape, proof_ratio downgrade 1.0 →
  0.5, risk flags) and `tests/test_prompt_integrity.py`
  (evidence_reading.md exists + renders completely). Suite: **586 passed /
  1 deselected**.
- **Live verification**: `scripts/demo_autopilot.py --verify
  --calibration-feedback met_expectations` (Nova backend, session
  `9f025266-26b8-4cbe-8b8c-b883c5436eea`, verdict `hire`): **VERIFY OK (all
  checks passed)** and `evidence_reading` present in the persisted brain.
  Captures committed: `docs/aura/output/brain_view_v3.json` +
  `docs/aura/output/summary-9f025266.json`.

## [AURA-1.7][bug-basin-closure] — 2026-08-09
- **Engine-bug closure (B1–B8 from `docs/aura/engine_plan.md`)**:
  - **B1 duplicate question + snapshot** — `question_generator.py` now enforces
    a hard invariant at the single emission point: the emitted question is
    never byte-identical to the one just asked (rotates the fallback bank via
    `_distinct_from_last_question`). `v5_brain_persister._append_timeline`
    upserts one `brain_snapshot` row per (session, question_number) instead of
    appending a second row on the finalize save (15 events / 14 questions).
  - **B3 difficulty mismatch** — `difficulty_governor` tracks
    `max_difficulty_reached` monotonicly; every `difficulty_reached` read site
    (assembler difficulty_state/calibration_state, reflection, hiring decision,
    sufficiency, report) now reports the peak instead of the closing level.
  - **B7 stale candidate memory** — `_consolidate` is recency-aware: the latest
    round is authoritative, later rounds win de-dup ordering, and an old
    weakness/risk ages out when a newer round's strengths refute it (prior
    "limited testing" no longer persists past a strong-testing round).
  - **B8 cross-layer shape drift** — `difficulty_state.evidence_depth` (a raw
    count) renamed to `evidence_total` so it never collides with
    calibration's labeled `evidence_depth`; frontend difficulty_state panel
    updated. The headline-vs-calibrated score gap remains intended
    (calibration override, documented in AURA-1.5).
  - **B5 / B6 verified in code** — hypothesis evidence deduped by id in
    `update_hypotheses` + `collect_evidence_for_hypothesis` (≤2 records/answer,
    top-dimension only); coverage counts only competencies that meet
    `evidence_count ≥ min ∧ gap ≤ threshold`, and zero-evidence required
    competencies are backfilled (gap=1.0). **B2 / B4 confirmed decided** —
    downgrade-only `effective_claim` (AURA-1.6) and `cross_answer_risk`.
- **Tracker**: `docs/aura/engine_plan.md` statuses updated to ✅ with dates.
- **Tests**: 6 new regressions — B1 snapshot upsert, B3 governor peak +
    fallback helper, B7 stale-weakness + absence-is-not-refutation, B8
    difficulty_state shape. Suite: **592 passed / 1 deselected**; frontend
    `tsc --noEmit` clean.

## [AURA-1.7-demo][demo-real-candidate] — 2026-08-09
- **Demo brains now start from a real candidate, not a stub** —
  `scripts/build_brain_demo.py` loads the seeded `CandidateProfile` (Alex
  Rivera / Jamie Chen) from the DB and shapes `candidate_profile` +
  `resume_text` exactly like the live WS session
  (`interview_ws._load_candidate_profile_data`), replacing the hardcoded
  `aura_test_candidate` stub. The demo `candidate_memory.candidate_id` is now
  the real profile id, and the strengths/weaknesses/initial hypotheses are
  resume-derived. `use_rag`/`use_llm` flags now flow through (already
  default-off; degrades to deterministic when no keys are set).
- **Regenerated** `out/brain_senior_backend_engineer.json` +
  `out/brain_senior_frontend_engineer.json` (pre-interview state:
  `evidence_total 0`, 6 hypotheses).

_Next entries appended below as changes are confirmed and tested.__
