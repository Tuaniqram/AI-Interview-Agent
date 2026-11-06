# 08 — Reasoning core

> Last updated: 2026-08-09 · Tag: [AURA-1.6][evidence-reading]

## Hypotheses

Each competency gets a hypothesis ("Candidate demonstrates X") with:
`competency`, `direction`, `confidence`, `probability`, `status`
(`untested`/`testing`/`confirmed`/`refuted`), `supporting_evidence`,
`contradicting_evidence`, `required_evidence`, `importance`.

- Seeded from `initial_hypotheses` intelligence or `generate_initial_hypotheses`
  (`app/brain/hypothesis_engine.py`).
- `attach_evidence_requirements` applies per-competency minimums from
  `evidence_requirements` / `default_min_evidence`.
- Updated each turn from extracted evidence (`update_hypotheses`).
- `_seed_hypothesis_for_competency` guarantees a fresh open hypothesis when the
  planner rotates to a competency — the interview never deadlocks on a null target.

## Evidence

Typed records: `{competency, dimension, score, confidence, evidence_text,
source_question, question_number, hypothesis_id, hypothesis_relevance}` stored in
`evidence_store`. `extracted_evidence` per turn flows into hypotheses and the
competency summary. Evidence levels follow the core prompt: mentioned →
demonstrated → proven.

## Depth checking (`missing_evidence_for`, brain/hypothesis_engine.py:36)

A hypothesis is "proven" when its competency's sub-capabilities
(`COMPETENCY_CHILDREN` from `app/data/competency_graph.py`) appear in the
collected evidence text. Anything past ~5 collected records is "enough"; the
missing list is `sub-capabilities not yet covered` (max 1…`required*2 − collected`).

## Evidence reading (semantic signals — AURA-1.6)

`app/agents/reasoning/evidence_reading.py` turns the LLM's read of the **raw
answers** into structured signals the deterministic layers consume:

- `effective_claim` is the **downgrade-only** rule — `min(semantic, regex)` over
  mentioned < demonstrated < proven. The LLM can only confirm or downgrade a
  claim, never inflate it past what the deterministic (regex) signals already
  support. `classify_claim` / `evidence_summary_stats`
  (`app/brain/evidence_reasoner.py`) apply it per record, so
  `calibration_state.proof_ratio` and the decision layers reflect the semantic
  correction deterministically.
- `map_evidence_reading` normalizes the LLM output into the canonical
  `evidence_reading` dict: only declared fields are accepted, hallucinated
  evidence ids and invalid enums are dropped — a fabricated id can never enter
  the brain.
- `evidence_reading_risk_flags` adds off-rubric red flags, cross-answer risks
  and unverified-claim counts to `decision_state.risk_flags` (additive only).
- `transcript_payload` size-caps the transcript sent to the model.

Run at finalization by `evidence_reading_node`
(`app/agents/evaluation/evidence_reading.py`); it is best-effort — any failure
degrades to the deterministic path (state returned unchanged).

## Uncertainty (`hypothesis_uncertainty`, :69)

`0..1`, = importance-weighted doubt:
- confirmed/refuted → floor 0.1
- untested → `1.0` (low prior) / `0.85` (high prior), scaled by `importance/10`
- decays with evidence count (`*max(0.35, 1 − 0.12*n)`)

`uncertainty_map` (:132) merges hypothesis uncertainty with the competency gap
component (`gap * 0.6`) for the planner.

## Contradictions & consistency

`contradiction_detector` + `contradiction_engine`:
- Evidence that contradicts a competency's prior average is flagged with severity
  (high/medium/low).
- `evaluate_sufficiency` (`contradiction_engine.py:251`) computes coverage
  (weighted), high-priority ratio, resolved-hypothesis ratio, and the
  recommendation/verdict with difficulty caps.
- `consistency_checks` compare answers across turns at finalize.

## Calibration (`app/brain/calibration.py`)

Assembles `calibration_state`: evidence depth (low/…), proof ratio, and the
**director gate**. A shallow evidence base blocks difficulty ratchet-up
(`_calibration_shallow` in difficulty_engine.py:193).

### Family-aware composite & F6 calibration (T2)

`app/data/rubrics.py` is the single source of truth for deterministic scoring:
`dimension_weights(category)` importance-weights the composite per family —
tech scores `technical` highest; the 8 non-tech families score `domain`
highest and zero `technical`, so a composite is never inflated by a dimension
the role does not exercise. The evaluator emits only `active_dimensions`
(`candidate_evaluator.py`), and `reconcile_composite` (`scoring.py:88`) applies
the family weights deterministically. F6 calibration (`_apply_evaluator_calibration`,
`scoring.py:201`) is family-aware too: `evidence_keywords(category)` supplies
the family's concrete-evidence keyword set and sign-bounding applies only to
dimensions the family scores.

## Candidate memory (`app/brain/candidate_memory.py`)

Learned `learned_strengths`, `learned_weaknesses`, `learned_risk_signals` from
prior sessions — fed to the evaluator (`_memory_context`) and the question
generator as prior context, never trusted verbatim.

## Difficulty

`role_difficulty_floor` (difficulty_engine.py:150): a Senior interview never
stays at difficulty 1. `difficulty_governor` (:203):
- deterministic window rule on the last-3 per-question evidence scores
  (>8.3 → +1, <7.0 → −1, else 0),
- hard clamps applied after any path: strong answers never lower it, weak never
  raise it; role floor always applies; shallow calibration blocks upward moves.

## Interview modes / actions

The director selects actions (`CONTINUE`/`PROBE`/`CHALLENGE`/`CLOSE`); question
generation modes are EXPLORER (open a competency), PROBER (drill detail),
CHALLENGER (stress seniority), VERIFIER (measure a specific claim), CLOSER
(wrap up). Claim verification is mandatory when `claims_to_verify` is present.
