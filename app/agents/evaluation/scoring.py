"""V5 explainable scoring — deterministic layer over LLM observations.

The LLM evaluator returns a raw ``composite_score`` that is opaque and noisy.
This module recomputes the composite deterministically from the per-dimension
scores via a fixed rubric, and emits ``score`` + ``reasons`` so every number
can be traced back to a dimension, its weight and its confidence.

Default rubric (documented, overridable per interview style via
``evaluator_weights``):

    technical      30%   domain correctness/depth
    reasoning      25%   logical structure & tradeoff analysis
    communication  20%   clarity and articulation
    confidence     10%   calibrated certainty
    behavioral     10%   ownership and collaboration
    completeness    5%   coverage of the question

Pure capability: state in → state out, no DB, no mutation of shared state.
"""
import logging

logger = logging.getLogger(__name__)

DEFAULT_DIMENSION_WEIGHTS = {
    "technical": 0.30,
    "reasoning": 0.25,
    "communication": 0.20,
    "confidence": 0.10,
    "behavioral": 0.10,
    "completeness": 0.05,
}

__all__ = [
    "DEFAULT_DIMENSION_WEIGHTS",
    "reconcile_composite",
    "rubric_breakdown",
    "build_score_reasons",
    "explainable_scoring_node",
]


def _weights(weights: dict | None) -> dict:
    merged = dict(DEFAULT_DIMENSION_WEIGHTS)
    if weights:
        merged.update({k: v for k, v in weights.items() if isinstance(v, (int, float))})
    total = sum(merged.values()) or 1.0
    return {k: v / total for k, v in merged.items()}


def reconcile_composite(
    evaluation: dict,
    weights: dict | None = None,
    confidence_weighted: bool = False,
) -> tuple[float | None, list[dict]]:
    """Recompute the composite score deterministically from per-dimension scores.

    Returns ``(composite, contributions)`` where each contribution is
    ``{"dimension", "weight", "score", "confidence", "contribution"}``. The
    composite is the weighted sum of the contributing scores, optionally
    tempered by each dimension's confidence.
    """
    w = _weights(weights)
    total_weight = 0.0
    weighted_sum = 0.0
    contributions: list[dict] = []

    for dim in w:
        dim_data = evaluation.get(dim)
        score = dim_data.get("score") if isinstance(dim_data, dict) else None
        if score is None:
            continue
        score = float(score)
        confidence = float(dim_data.get("confidence", 0.5)) if isinstance(dim_data, dict) else 0.5
        effective = score * confidence if confidence_weighted else score
        weight = w[dim]
        weighted_sum += effective * weight
        total_weight += weight
        contributions.append({
            "dimension": dim,
            "weight": round(weight, 4),
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "contribution": round(effective * weight, 4),
        })

    if not contributions or total_weight == 0:
        return None, []

    composite = round(weighted_sum / total_weight, 2)
    return composite, sorted(contributions, key=lambda c: c["contribution"], reverse=True)


def rubric_breakdown(evaluation: dict, weights: dict | None = None) -> list[dict]:
    """The per-dimension contribution table (descending by contribution)."""
    _, contributions = reconcile_composite(evaluation, weights)
    return contributions


def build_score_reasons(
    evaluation: dict,
    composite: float | None,
    contributions: list[dict],
    evidence_records: list[dict] | None = None,
    competency_summary: dict | None = None,
) -> list[str]:
    """Human-readable, traceable reasons for a composite score.

    One reason per contributing dimension plus evidence-quality notes drawn
    from the Phase-3 signals (strength, contradiction) and a composite summary.
    """
    if not contributions:
        return ["No scored dimensions available; composite score not computed."]

    reasons = []
    for c in contributions:
        confidence_note = (
            f" (confidence {c['confidence']:.2f})"
            if c["confidence"] < 0.6
            else ""
        )
        reasons.append(
            f"{c['dimension']} ({c['weight'] * 100:.0f}% weight): "
            f"{c['score']:.1f}/10 → {c['contribution']:.2f} composite{confidence_note}"
        )

    if evidence_records:
        scored = [
            ev for ev in evidence_records
            if ev.get("score") is not None and ev.get("dimension") in {c["dimension"] for c in contributions}
        ]
        if scored:
            strongest = max(scored, key=lambda ev: ev.get("strength", 0.0))
            reasons.append(
                f"Strongest evidence: {strongest['dimension']} strength {strongest.get('strength', 0.0):.2f}"
            )
        contradictions = [ev for ev in scored if ev.get("contradiction")]
        if contradictions:
            reasons.append(
                f"{len(contradictions)} evidence record(s) contradict the competency's prior average"
            )

    if composite is not None:
        reasons.append(
            f"Composite {composite:.2f} = weighted average of "
            f"{len(contributions)} scored dimension(s)"
        )
    return reasons


def explainable_scoring_node(state: dict) -> dict:
    """Replace the opaque LLM composite with a deterministic, explained score.

    Keeps the same state contract as the evaluator node so the engine can slot
    it in after evaluation/evidence extraction without changing the flow.
    """
    evaluation = state.get("unified_evaluation") or {}
    weights = (state.get("interview_style") or {}).get("evaluator_weights")
    confidence_weighted = bool(
        (state.get("interview_style") or {}).get("confidence_weighted", False)
    )

    composite, contributions = reconcile_composite(
        evaluation, weights, confidence_weighted=confidence_weighted
    )
    if composite is None:
        logger.info("Explainable scoring: no scored dimensions, keeping prior score")
        return state

    reasons = build_score_reasons(
        evaluation,
        composite,
        contributions,
        evidence_records=state.get("evidence_store") or [],
        competency_summary=state.get("competency_summary") or {},
    )

    return {
        **state,
        "evaluation_score": composite,
        "score_contributions": contributions,
        "score_reasons": reasons,
    }
