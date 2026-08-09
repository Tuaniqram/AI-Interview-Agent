# AURA Engine — `brain_view.json` change tracker

> Last updated: 2026-08-09 · Tag: [AURA-1.3][T4-calibration-ranking]

`brain_view.json` is the captured output of `GET /api/v1/intelligence/brain/{sid}`
(`app/api/v1/intelligence.py`), the full post-interview brain snapshot used by
debugging, demo autopilot and downstream review. This file tracks every change to
that output as the engine evolves. Schema changes (new/removed/renamed keys) and
semantic changes (values that differ for new sessions) are both recorded here.

## Output schema (stable)

The endpoint serializes persisted rows (`InterviewBrain`, `EvidenceGraph`,
`InterviewTimeline`) into a fixed shape:

| Key | Source | Contents |
|---|---|---|
| `session_id` | URL path | Session UUID |
| `interview_brain.version` | `InterviewBrain.version` | Brain schema version |
| `interview_brain.current_hypotheses` | `InterviewBrain.current_hypotheses` | Hypothesis list w/ status, confidence, evidence ids |
| `interview_brain.evidence_summary` | `InterviewBrain.evidence_summary` | Per-competency gap / score aggregates |
| `interview_brain.competency_scores` | `InterviewBrain.competency_scores` | Per-competency score arrays + averages |
| `interview_brain.difficulty_profile` | `InterviewBrain.difficulty_profile` | Adaptive difficulty dims + level |
| `interview_brain.decision_state` | `InterviewBrain.decision_state` | `director`, `consistency_checks`, `evidence_sufficiency`, `hiring_recommendation` |
| `evidence_graph.nodes` / `.edges` | `EvidenceGraph.nodes` / `.edges` | Evidence→hypothesis support graph |
| `timeline[]` | `InterviewTimeline` | Ordered brain snapshots per question |

Reference capture: `D:\UnityTemp\opencode\aura-run\brain_view.json` (session
`d0e0b2e7-3faf-46db-b6bb-a81b8415dba1`, 2026-08-07, pre-T2 values).

## Change ledger (append-only)

### 2026-08-09 · AURA-1.2 T2 scoring — value changes for new sessions, no shape change
- **Affects**: `interview_brain.competency_scores` (averages), `evidence_summary`
  (per-competency aggregates), `decision_state.consistency_checks` (dimension
  scores), `decision_state.hiring_recommendation.composite_score`.
- **What changed**: `app/data/rubrics.py` is now the single source of truth for
  scoring weights; `reconcile_composite` (scoring.py) computes the composite with
  family-aware, importance-weighted `dimension_weights` instead of the fixed
  technical default; evaluator calibration sign-bounds only active dimensions.
  For non-tech families the composite is no longer inflated by a zeroed
  `technical` dimension. For tech-family roles the numbers are largely unchanged.
- **No shape change**: no keys added, removed or renamed; stored rows from
  sessions before this change are untouched and still render as-is.
- **Outside brain_view**: T2 also changed evaluator prompt variables
  (`{{rubric}}`, `{{primary_dimension}}`) — prompt-only, not serialized here.

### 2026-08-09 · AURA-1.3 T4 calibration loop + ranking — no change to brain_view
- **No change**: the calibration loop (`calibration_feedback` table,
  `/orgs/{org_id}/calibration/*`) and the calibrated/comparable ranking
  (`/candidates/ranking`) read the persisted brain but never write into the
  columns brain_view serializes. No keys added or removed.
- **Predicted values used by calibration** come from
  `interview_brain.brain_metadata.calibration_state`, which is **not** part of
  the brain_view output — by design, so the recruiter-facing snapshot stays
  stable while the feedback loop grows.

## Compatibility rule

The brain_view contract is **additive-only**: a change may only add optional
keys or alter values for new sessions; it must never remove or rename an existing
key, because stored rows and the demo autopilot depend on the current shape.
Any change that breaks this rule requires a new `interview_brain.version`.
