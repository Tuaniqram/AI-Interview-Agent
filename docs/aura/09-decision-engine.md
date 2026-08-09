# 09 — Decision engine

> Last updated: 2026-08-09 · Tag: [AURA-1.6][evidence-reading]

## Canonical composite (`compute_canonical_score` — contradiction_engine.py:176)

The single score every downstream component uses:

```
canonical = competency_average_score * 0.5
          + (hypothesis_confidence * 10) * 0.3
          + (coverage_ratio * 10)        * 0.2
```

- `competency_average_score` = **weighted** average of per-competency
  `average_score` by `weight`.
- `hypothesis_confidence` = confirmed/(confirmed+refuted), else evidence confidence.
- `coverage_ratio` = covered-weight/total-weight over the required set
  (`evaluate_sufficiency`).

Sources: the recommendation's `composite_score`; recomputed by
`canonical_score_from_state` for stages before a recommendation exists.

## Hiring decision (`compute_decision_score` — decision_engine.py:77)

```
difficulty_credit = min(1.0, 0.55 + 0.09 * difficulty)     # d1=0.64 d3=0.82 d5=1.0
score = holistic * difficulty_credit
      + (coverage - 0.5) * 2.0
      + (confirmed - 0.5) * 2.0
      − 1.5 * min(contradictions, 3)/3      # when >= BORDERLINE_CONTRADICTION_CAP
```

- Holistic anchors; coverage/confirmed pull toward extremes; contradictions pull
  to the middle; difficulty credits evidence earned at the top of the scale.
- `MIN_EVIDENCE_FOR_DECISION` guards — below it the verdict is
  `insufficient_evidence`.

## Verdict map (7-point, `map_decision`)

| score | verdict |
|---|---|
| ≥ 8.5 | strong_hire |
| ≥ 7.5 | hire |
| ≥ 6.5 | lean_hire |
| ≥ 5.0 | insufficient_evidence |
| ≥ 4.0 | lean_no_hire |
| ≥ 2.5 | no_hire |
| else | strong_no_hire |

## Coverage caps (F4)

- `strong_hire` requires coverage ≥ `STRONG_HIRE_MIN_COVERAGE`, else demote to `hire`.
- `hire` requires coverage ≥ `HIRE_MIN_COVERAGE`, else demote to `lean_hire`.
- Caps set `flag_review` and append to the rationale.

## Decision review (`decision_review.py`)

Draft → self-review → final:
- checks: `insufficient_evidence`, `missing_competency`/low coverage, `overconfidence`
  (high confidence on weak evidence), `contradictions`.
- `finalize_decision` (F9): any high-severity issue caps confidence at 0.5 and
  demotes decisive verdicts to `insufficient_evidence`; contradictions −0.2
  confidence; overconfidence −0.1; sets `flag_review`.

### Semantic review checks (AURA-1.6)

The evidence reading adds checks (`off_rubric_flag`, `cross_answer_risk`,
`unverifiable_claims`) whose severity is **capped at `medium`** — they flag for
review and trim confidence, but can never alone demote a decisive verdict
(demotion requires a deterministic high-severity check). The reading's flags
also land in `decision_state.risk_flags` via `evidence_reading_risk_flags`
(additive only).

## Difficulty caps on verdicts (recommendation layer)

`_DIFFICULTY_VERDICT_CAPS = {1: "borderline", 2: "borderline", 3: "hire", 4: "hire"}`
— a session stuck at difficulty 1-2 can never recommend hire, matching the
decision engine's difficulty credit so the two layers never contradict.

## Recommendation fields

`{verdict, confidence, confidence_v2, coverage_ratio, composite_score,
confirmed_hypotheses, refuted_hypotheses, testing_hypotheses,
contradictions_found, average_confidence, difficulty_reached, unanswered_hypotheses}`.

## Next steps by verdict (`decision_next_steps`)

hire → offer discussion; lean_hire → reference check; reject → archive +
calibration feedback; else → probe round / compare shortlist.

## Calibration loop (T4) — measure + report drift

Deterministic, no LLM, no auto-tuning. The **predicted** side is the already-
computed `calibration_state` persisted per session at finalize
(`calibrated_verdict`, `calibrated_score`, `difficulty_reached`, `role_floor`);
recruiters record the **actual** post-hire outcome via
`PUT /orgs/{org_id}/calibration/feedback/{session_id}`, which snapshots the
predicted side into `calibration_feedback`.

Drift math (`app/services/calibration_service.py`, pure):
- Coarse buckets — predicted verdict → `hire`/`lean_hire`/`no_hire`/`uncertain`
  (`strong_hire`→hire, `borderline`/`insufficient_evidence`/`review`→uncertain);
  actual outcome → `hire` (strong_performance), `lean_hire`
  (met_expectations), `no_hire` (below_expectations / terminated during
  probation), `uncertain` (no_feedback).
- Per session: `correct` | `over_predict` | `under_predict` | `uncertain`
  (bucket-order comparison; non-committal predictions never count).
- Difficulty-credit bands reuse the calibration credit formula
  (`min(0.4, 0.1·(reached − floor + 1))` when the floor is met, `−0.4` when
  not) → `>=0.3 (deep)` / `0.1-0.3` / `0-0.1` / `floor unmet`.
- `GET .../calibration/drift` aggregates correctness + over/under by family
  (`detect_family`) and band, and emits insight strings for structural drift
  (agreement < 60%, systematic over/under-prediction, band/family
  over-prediction). `GET .../calibration/drift/summary` returns headlines.

### Comparable ranking (T4)

Calibrated scores are only directly comparable within a family cohort. The
`/ranking` endpoint surfaces `family` per candidate and a `comparable_note`
when a candidate's family differs from the cohort's dominant family; scoring
anomalies across families are visible via the per-family drift report above.
