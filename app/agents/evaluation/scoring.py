"""V5 explainable scoring — deterministic layer over LLM observations.

The LLM evaluator returns a raw ``composite_score`` that is opaque and noisy.
This module recomputes the composite deterministically from the per-dimension
scores via a family rubric, and emits ``score`` + ``reasons`` so every number
can be traced back to a dimension, its weight and its confidence.

Rubrics live in ``app/data/rubrics.py`` (T2). The default rubric is the tech
one; family roles resolve their own dimension weights (domain-first, T1) and
their own F6 calibration keywords. An interview style may still override any
dimension weight via ``evaluator_weights``.

Default tech rubric (documented, overridable per interview style via
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
import re

from app.data.rubrics import (
    RUBRIC_DIMENSIONS,
    category_from_taxonomy,
    dimension_weights,
    domain_label_for,
    evidence_keywords,
    normalize_category,
    ownership_words,
    quantification_terms,
    rubric_for_category,
)

logger = logging.getLogger(__name__)

DEFAULT_DIMENSION_WEIGHTS = dict(dimension_weights("technical"))

# Calibration rubric (P5): maps any composite onto a score band with a fixed
# anchor so the same number gets the same label everywhere.
CALIBRATION_BANDS = (
    (9.5, "outstanding"),
    (8.2, "strong"),
    (6.5, "average"),
    (4.8, "weak"),
)

__all__ = [
    "DEFAULT_DIMENSION_WEIGHTS",
    "CALIBRATION_BANDS",
    "score_band",
    "reconcile_composite",
    "rubric_breakdown",
    "build_score_reasons",
    "explainable_scoring_node",
]


def score_band(composite: float) -> str:
    """Calibration label for a composite score (P5)."""
    for threshold, label in CALIBRATION_BANDS:
        if composite >= threshold:
            return label
    return "poor"


def _any_depth_probe(state: dict) -> bool:
    """Whether any VERIFIER/PROBER/CHALLENGER follow-up probe has been asked."""
    for q in state.get("questions_asked") or []:
        if q.get("mode") in ("VERIFIER", "PROBER", "CHALLENGER"):
            return True
    return False


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


def _category_for_competency(state: dict) -> str | None:
    """The category of the current target competency, from the session taxonomy.

    T2: the scoring node needs the family to pick the right rubric (weights +
    calibration keywords). Falls back to ``None`` (tech default) when the
    target cannot be resolved.
    """
    return category_from_taxonomy(
        state.get("competency_taxonomy"),
        (state.get("question_objective") or {}).get("target_competency") or "",
    )


def _apply_evaluator_calibration(evaluation: dict, category: str | None = None) -> dict:
    """Adjust overly optimistic evaluator scores when evidence lacks substance.

    This calibration is opt-in via the interview style to preserve test expectations
    in CI/default local runs. When enabled (AURA enables it — F6 score discipline):

        score >= 8   without a concrete example keyword      -> 7.0
        score >= 8.5 without quantification (numbers/units)  -> 8.0
        score >= 9   without ownership signals               -> 8.0

    So 8+ only stands when the answer demonstrably contains concrete, ideally
    quantified, evidence. T2: the evidence/ownership keywords and the
    quantification terms are family-aware (``app/data/rubrics.py``) so a
    Marketing Manager's "campaign funnel" reads as concrete evidence just as a
    backend engineer's "architecture tradeoff" does.
    """
    if not evaluation:
        return evaluation
    family_keywords = evidence_keywords(category)
    family_ownership = ownership_words(category)
    calibrated = dict(evaluation)
    for dim, dim_data in list(calibrated.items()):
        if not isinstance(dim_data, dict):
            continue
        score = dim_data.get("score")
        evidence = (dim_data.get("evidence") or "")
        if score is None:
            continue
        try:
            score_f = float(score)
        except Exception:
            continue
        if score_f >= 8.0:
            evidence_l = evidence.lower()
            has_example = any(k in evidence_l for k in family_keywords)
            has_quantification = _has_quantification(evidence_l, category)
            if not has_example:
                calibrated[dim] = dict(dim_data)
                calibrated[dim]["score"] = 7.0
            else:
                if score_f >= 8.5 and not has_quantification:
                    calibrated[dim] = dict(dim_data)
                    calibrated[dim]["score"] = 8.0
                elif score_f >= 9.0 and not any(w in evidence_l for w in family_ownership):
                    calibrated[dim] = dict(dim_data)
                    calibrated[dim]["score"] = 8.0
    return calibrated


def _has_quantification(text: str, category: str | None = None) -> bool:
    """Does the evidence reference a measured quantity (40%, 9x, 20ms, 10k)?"""
    if not text:
        return False
    terms = "|".join(re.escape(t) for t in quantification_terms(category))
    return bool(re.search(
        r"(?<!\w)\d+(?:\.\d+)?\s*(?:%|[x×]|ms|s\b|secs?|seconds|req/s|qps|rps|tps|"
        r"users|requests|concurrent|gb|tb|mb|hours|days|weeks|usd|\$|k|m|million|thousand)\b",
        text,
    )) or bool(re.search(
        r"\b(reduced?|increased?|cut|saved|boosted|optimized|dropped|halved|doubled|"
        r"tripled|grew|scaled|achieved)\b[\s\S]{0,40}\d",
        text,
    )) or (bool(terms) and re.search(
        rf"\b(?:{terms})\b[\s\S]{{0,40}}\d",
        text,
    ))


def explainable_scoring_node(state: dict) -> dict:
    """Replace the opaque LLM composite with a deterministic, explained score.

    Keeps the same state contract as the evaluator node so the engine can slot
    it in after evaluation/evidence extraction without changing the flow.
    """
    evaluation = state.get("unified_evaluation") or {}
    # T2: weights come from the family rubric (resolved by the target
    # competency's category), overridable per style via ``evaluator_weights``.
    category = _category_for_competency(state)
    style_weights = (state.get("interview_style") or {}).get("evaluator_weights")
    weights = dimension_weights(category, style_weights)
    confidence_weighted = bool(
        (state.get("interview_style") or {}).get("confidence_weighted", False)
    )

    # Calibration is opt-in via interview style to avoid unexpected changes in tests
    apply_calibration = bool((state.get("interview_style") or {}).get("apply_evaluator_calibration", False))
    eval_for_scoring = (
        _apply_evaluator_calibration(evaluation, category) if apply_calibration else evaluation
    )

    composite, contributions = reconcile_composite(
        eval_for_scoring, weights, confidence_weighted=confidence_weighted
    )
    if composite is None:
        logger.info("Explainable scoring: no scored dimensions, keeping prior score")
        return state

    reasons = build_score_reasons(
        eval_for_scoring,
        composite,
        contributions,
        evidence_records=state.get("evidence_store") or [],
        competency_summary=state.get("competency_summary") or {},
    )

    band = score_band(composite)
    # P5: a high score that has never been stress-tested is an unverified
    # claim — say so instead of letting it stand as established evidence.
    if composite >= 8.2 and not _any_depth_probe(state):
        reasons.append(
            f"Calibration: composite {composite:.2f} ({band}) not yet verified — "
            "no VERIFIER/PROBER/CHALLENGER follow-up probe has been asked"
        )

    return {
        **state,
        "evaluation_score": composite,
        "score_band": band,
        "score_contributions": contributions,
        "score_reasons": reasons,
    }
