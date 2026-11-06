# Engine Plan — AURA Interview Engine Evaluation & Fixes

Tracking the evaluation of the AURA interview engine from the full 13-layer brain
JSON of a real session, and the fixes that come out of it.

## Evaluation source

- Session: `9f025266-26b8-4cbe-8b8c-b883c5436eea` (Senior Backend Engineer, verdict hire)
- Brain JSON snapshot: `docs/aura/output/brain-9f025266-26b8-4cbe-8b8c-b883c5436eea.json`
  (full `GET /api/v1/intelligence/brain/{sid}` payload — all 13 `brain_layers` + evidence_graph + timeline)
- Engine eval status: **audited 2026-08-09**

## What the engine gets right (keep)

- [x] Multi-layer brain is internally consistent — shared IDs across hypotheses /
  evidence / competencies / decision.
- [x] Downgrade-only calibration refuses to over-claim (`proof_ratio 0.0`,
  `decision_confidence 0.09`, honest risk flags on a 8.55 composite).
- [x] Adaptive questioning (`challenge` mode → `tech_data_modeling`, difficulty
  escalation to level 5).
- [x] Contradiction detection caught the bot-like score pattern (4 flags, 1 contradict edge).
- [x] Sufficiency is honest (`coverage 0.86`, `is_sufficient false`, 1 gap).

## Findings (engine issues) → fix status

| ID | Issue | Evidence | Status |
|----|-------|----------|--------|
| B1 | Duplicate final question + duplicate snapshot | Q13 == Q14 text/answer byte-identical; timeline has two Q14 snapshots (15 events / 14 questions) | ✅ fixed 2026-08-09 |
| B2 | Semantic evidence reading discarded in calibration | `effective_claim` downgrade-only zeroes the 4 "demonstrated" reads → `proof_ratio 0.0`, `decision_confidence 0.09` | ✅ decided — downgrade-only by design (AURA-1.6) |
| B3 | Difficulty mismatch between layers | Timeline reaches difficulty 5 (Q8–Q11) but `difficulty_state.difficulty_reached = 3` | ✅ fixed 2026-08-09 |
| B4 | Repeated/canned answer content not detected | Same answer text for Q2,3,4,6,7,8 and Q13/Q14; only score-inconsistency caught | ✅ fixed — `cross_answer_risk` review check (AURA-1.6) |
| B5 | Per-hypothesis evidence overcount | Hypothesis `7feeb809` ev=4/2 vs competency/typed-graph 3 (shared evidence not deduped) | ✅ verified — deduped by evidence id in `update_hypotheses` + `collect_evidence_for_hypothesis`; ≤2 records/answer |
| B6 | Coverage metric ignores untested competencies | 6/14 hypotheses untested (core/framework/communication at placeholder 0.5) yet coverage 86% | ✅ verified — zero-evidence competencies backfilled (gap=1.0, AURA-1.5); coverage counts only `evidence_count ≥ min ∧ gap ≤ threshold` |
| B7 | Stale candidate memory | Prior "limited testing" weakness persists though testing answers were strongest | ✅ fixed 2026-08-09 |
| B8 | Cross-layer shape drift | `evidence_depth` "high" (calibration) vs 13 (difficulty); headline 8.55/0.71 vs calibrated 6.5/0.09 | ✅ fixed (shape) + decided (values) 2026-08-09 |

## Execution order

1. **B1** — prevent the close-loop from re-asking the same question / double snapshot. ✅ 2026-08-09
2. **B5** — dedupe evidence across hypotheses in `build_hypothesis_brain`. ✅ verified in code
3. **B4** — duplicate-answer content detector in the evidence pipeline. ✅ `cross_answer_risk` (AURA-1.6)
4. **B3** — reconcile `difficulty_state.difficulty_reached` with the timeline max. ✅ 2026-08-09
5. **B2 / B6 / B7 / B8** — need explicit decisions before changing behavior. ✅ decisions made 2026-08-09

## Verification

- Backend: run `pytest` for affected modules (`tests/test_v5_agents.py`,
  `tests/test_evidence_quality.py`, hypothesis/decision tests).
- Frontend: `tsc --noEmit` + `vite build` after any display changes.
- Data: re-dump the brain JSON for the same session and re-run this audit.
