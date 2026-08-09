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

## [AURA-1.3][T3-calibration-ranking] — 2026-08-09
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
  tracks T1-taxonomy / T2-scoring / T3-calibration-ranking completion status.
- **Verification**: `python -m pytest -q` → 565 passed (526 pre-existing + 39
  new for T2/T3), zero external services; `alembic heads` resolves to the
  calibration-feedback migration.

_Next entries appended below as changes are confirmed and tested.__
