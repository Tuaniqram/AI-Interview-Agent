"""Explainable scoring: deterministic composite from the LLM observations,
traceable reasons, rubric breakdown, and the scoring node wiring."""
from tests.conftest import make_v4_state

from app.agents.evaluation.scoring import (
    DEFAULT_DIMENSION_WEIGHTS,
    build_score_reasons,
    explainable_scoring_node,
    reconcile_composite,
    rubric_breakdown,
    score_band,
)

_EVAL = {
    "technical": {"score": 8.0, "confidence": 0.9, "evidence": "x"},
    "reasoning": {"score": 6.0, "confidence": 0.7, "evidence": "y"},
    "communication": {"score": 7.0, "confidence": 0.8, "evidence": "z"},
    "behavioral": {"score": None, "confidence": 0.0, "evidence": "n/a"},
    "confidence": {"score": None, "confidence": 0.0, "evidence": "n/a"},
    "completeness": {"score": None, "confidence": 0.0, "evidence": "n/a"},
}


def test_default_weights_sum_to_one():
    assert sum(DEFAULT_DIMENSION_WEIGHTS.values()) == 1.0
    assert DEFAULT_DIMENSION_WEIGHTS["technical"] == 0.30


def test_reconcile_composite_is_deterministic():
    c1, parts1 = reconcile_composite(_EVAL)
    c2, parts2 = reconcile_composite(_EVAL)
    assert c1 == c2
    expected = (8.0 * 0.30 + 6.0 * 0.25 + 7.0 * 0.20) / (0.30 + 0.25 + 0.20)
    assert c1 == round(expected, 2)
    assert len(parts1) == 3
    assert all(p["dimension"] != "behavioral" for p in parts1)


def test_reconcile_ignores_unscored_dimensions():
    composite, parts = reconcile_composite({"technical": {"score": 8.0, "confidence": 0.9}})
    assert composite == 8.0
    assert len(parts) == 1
    assert parts[0]["contribution"] == 2.4


def test_reconcile_returns_none_without_scores():
    composite, parts = reconcile_composite({"technical": {"score": None}})
    assert composite is None
    assert parts == []


def test_confidence_weighted_temps_down_scores():
    plain, _ = reconcile_composite(_EVAL)
    weighted, _ = reconcile_composite(_EVAL, confidence_weighted=True)
    assert weighted < plain


def test_custom_weights_augment_defaults():
    custom = {"technical": 0.5, "communication": 0.5}
    composite, parts = reconcile_composite(_EVAL, weights=custom)
    tech = next(p for p in parts if p["dimension"] == "technical")
    assert tech["weight"] > DEFAULT_DIMENSION_WEIGHTS["technical"]
    assert composite == 7.2


def test_rubric_breakdown_sorted_descending():
    parts = rubric_breakdown(_EVAL)
    contributions = [p["contribution"] for p in parts]
    assert contributions == sorted(contributions, reverse=True)
    assert parts[0]["dimension"] == "technical"


def test_build_score_reasons_are_traceable():
    composite, parts = reconcile_composite(_EVAL)
    reasons = build_score_reasons(_EVAL, composite, parts)
    assert any("technical" in r and "8.0/10" in r for r in reasons)
    assert any("weight" in r for r in reasons)
    assert any(str(composite) in r for r in reasons)


def test_build_score_reasons_note_low_confidence_and_contradictions():
    low_conf_eval = {
        "technical": {"score": 8.0, "confidence": 0.4, "evidence": "x"},
    }
    composite, parts = reconcile_composite(low_conf_eval)
    evidence = [
        {"dimension": "technical", "score": 8.0, "strength": 0.72, "contradiction": True},
    ]
    reasons = build_score_reasons(low_conf_eval, composite, parts, evidence_records=evidence)
    assert any("confidence 0.40" in r for r in reasons)
    assert any("contradict" in r for r in reasons)
    assert any("Strongest evidence" in r for r in reasons)


def test_explainable_scoring_node_replaces_composite_and_adds_reasons():
    from app.agents.evaluation.scoring import _apply_evaluator_calibration

    state = make_v4_state(
        unified_evaluation=_EVAL,
        evaluation_score=7.9,
        evidence_store=[
            {"dimension": "technical", "score": 8.0, "strength": 0.72, "contradiction": False},
        ],
    )
    out = explainable_scoring_node(state)
    style_weights = state["interview_style"].get("evaluator_weights")
    # AURA enables evaluator calibration (F6): the 8.0 technical with no
    # concrete example is capped to 7.0 before the composite is computed.
    expected = reconcile_composite(
        _apply_evaluator_calibration(_EVAL), weights=style_weights
    )[0]
    assert out["evaluation_score"] != 7.9
    assert out["score_reasons"]
    assert out["score_contributions"]
    assert out["evaluation_score"] == expected
    assert out["score_band"] == score_band(expected)


def test_score_band_calibration_labels():
    assert score_band(9.7) == "outstanding"
    assert score_band(9.5) == "outstanding"
    assert score_band(9.0) == "strong"
    assert score_band(8.2) == "strong"
    assert score_band(7.0) == "average"
    assert score_band(6.5) == "average"
    assert score_band(5.5) == "weak"
    assert score_band(4.8) == "weak"
    assert score_band(3.0) == "poor"


def test_scoring_node_flags_unverified_high_scores():
    # Evidence is concrete + quantified so F6 calibration keeps the 8.5s;
    # the composite still sits above the verification bar with no probe asked.
    high = {
        k: {"score": 8.5, "confidence": 0.9,
            "evidence": "Example: cut latency 40% on a production system I owned"}
        for k in ("technical", "reasoning", "communication")
    }
    state = make_v4_state(unified_evaluation=high, questions_asked=[])
    out = explainable_scoring_node(state)
    assert out["evaluation_score"] >= 8.2
    assert any("not yet verified" in r for r in out["score_reasons"])


def test_scoring_node_verification_note_clears_after_probe():
    high = {k: {"score": 8.5, "confidence": 0.9} for k in ("technical", "reasoning", "communication")}
    state = make_v4_state(
        unified_evaluation=high,
        questions_asked=[{"text": "How was that measured?", "competency": "tech_core", "mode": "VERIFIER"}],
    )
    out = explainable_scoring_node(state)
    assert not any("not yet verified" in r for r in out["score_reasons"])


def test_scoring_node_keeps_prior_score_without_scored_dims():
    state = make_v4_state(unified_evaluation={"technical": {"score": None, "confidence": 0.0}})
    out = explainable_scoring_node(state)
    assert out["evaluation_score"] is None
    assert out.get("score_reasons") is None


def test_family_calibration_trusts_family_evidence():
    from app.agents.evaluation.scoring import _apply_evaluator_calibration

    eval_ = {
        "domain": {"score": 8.5, "confidence": 0.9,
                   "evidence": "Ran a campaign that lifted conversion 40%"},
    }
    assert _apply_evaluator_calibration(eval_, "marketing")["domain"]["score"] == 8.5
    assert _apply_evaluator_calibration(eval_)["domain"]["score"] == 7.0


def test_scoring_node_resolves_family_weights_from_taxonomy():
    # The target competency's category (marketing) zeroes ``technical``, so a
    # stray technical score must not drag the composite down to the tech mix.
    state = make_v4_state(
        competency_taxonomy=[{"id": "mkt_brand", "category": "marketing"}],
        question_objective={"target_competency": "mkt_brand"},
        unified_evaluation={
            "domain": {"score": 8.0, "confidence": 0.9,
                       "evidence": "Example: ran a campaign and owned the launch"},
            "technical": {"score": 3.0, "confidence": 0.9, "evidence": "x"},
        },
    )
    out = explainable_scoring_node(state)
    assert out["evaluation_score"] == 8.0
