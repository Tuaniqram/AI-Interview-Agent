# Wave Plan — implementation status

> Status snapshot: 2026-08-09. Every item below is implemented, tested, and
> documented in `docs/aura` (CHANGELOG + affected sections). Tests: **565
> passing** (`pytest`, no external services).

## Wave 1 — T1-taxonomy ✅ (shipped `[AURA-1.1][T1-taxonomy]`)

- [x] **8 job families** added to `app/data/competency_taxonomy.py` (commerce,
      marketing, design, product, hr, finance, operations, customer_success —
      5 competencies each, 65 total / 12 categories); family competencies lead
      with the `domain` evidence dimension.
- [x] **Re-add 4 tech orphans** (`tech_event_driven`, `tech_deployment`,
      `tech_caching`, `tech_data_modeling`); `SKILL_TO_COMPETENCY` extended
      (e.g. `kafka` → `tech_event_driven`).
- [x] **Profiler unblock** — `role_competency_profiler.py` accepts the 8 new
      families (`detect_family`, family-aware `_suggest_from_taxonomy`).
- [x] **Resolver / role-brain family-awareness** — `DEFAULT_DIMENSIONS_BY_CATEGORY`
      + `_FALLBACK_WEIGHTS`; 8 new role classes, importance bases, 22 new
      must-prove probes.
- [x] **Prompts** — `role_competency_profiler.md` documents the 12
      prefixes/categories + `domain`-first rule.
- [x] **Tests** — taxonomy invariants, deterministic family-aware profiler,
      family role-brain, `derive_domain_label`.

## Wave 2 — T2-scoring ✅ (shipped `[AURA-1.2][T2-scoring]`)

- [x] **Rubrics** — `app/data/rubrics.py` is the single source of truth: 7
      dimensions + anchors, tech vs non-tech family weights (`domain`-led for
      families, `technical` zeroed).
- [x] **Importance-weighted scoring** — `reconcile_composite` resolves
      `dimension_weights(category)` deterministically; evaluator emits only
      `active_dimensions` with family `primary_dimension` + rendered `{{rubric}}`.
- [x] **Seniority-floor difficulty credit** — already shipped in the brain
      layers (`role_difficulty_floor`, `calibrated_quality`, D2 difficulty
      credit, director-gate floor clamp); T2 integrates with it.
- [x] **Family-aware calibration (F6)** — `_apply_evaluator_calibration` uses
      family keyed `evidence_keywords`; sign-bounding only on scored dimensions.
- [x] **`unified_evaluator.md`** — updated for the family-rubric contract
      (`{{rubric}}`, `{{primary_dimension}}`, family-resolved `{{domain_label}}`).
- [x] **Tests** — `tests/unit/data/test_rubrics.py` + scoring tests.

## Wave 3 — T4 calibration loop + cross-candidate ranking ✅ (shipped `[AURA-1.3][T3-calibration-ranking]`)

- [x] **T4 calibration loop — measure + report drift** (deterministic, no
      auto-tuning): `calibration_feedback` table (migration
      `b1a2c3d4e5f6`), predicted side snapshotted from the already-persisted
      `interview_brain.calibration_state`; `PUT .../calibration/feedback/{sid}`,
      `GET .../calibration/drift`, `GET .../calibration/drift/summary`.
      Drift math in `app/services/calibration_service.py` (verdict buckets,
      over/under/uncertain, difficulty-credit bands, insights).
- [x] **Cross-candidate ranking — calibrated + comparable**:
      `/candidates/ranking` rows carry `calibrated_score`, `difficulty_reached`,
      `role_floor`, `family`, `score_band`, `comparable_note`; `sort_by=final|calibrated`,
      `family` filter; `/summary` + `/export` backward compatible.
- [x] **Tests** — drift math unit tests, calibration API contract tests,
      ranking-helper tests (39 new).

## Coverage notes

- Every item above is documented in `docs/aura` (CHANGELOG `[AURA-1.1/1.2/1.3]`
  + the affected sections; `tests/` and `docs/` are gitignored local working
  artifacts by design).
- Scope decisions recorded during Wave 3: calibration loop is measure + report
  only (no auto-tuning); ranking work is backend-only (no frontend changes).
