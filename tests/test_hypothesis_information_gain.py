"""Information Gain Engine: entropy-based hypothesis selection (Phase 2).

Covers the pure functions in hypothesis_manager: the PRIOR_CONFIDENCE prior,
expected_information_gain scoring, and the next_target argmax (with the legacy
deep-probe fallback preserved). No LLM, no DB — fully deterministic.
"""
import pytest

from app.agents.reasoning.hypothesis_engine import (
    PRIOR_CONFIDENCE,
    _entropy,
    expected_information_gain,
    generate_initial_hypotheses,
    next_target,
    update_hypotheses,
)


def _hypothesis(**overrides) -> dict:
    base = {
        "id": "h1",
        "competency": "tech_core",
        "statement": "Candidate has strong tech_core skills",
        "direction": "positive",
        "confidence": PRIOR_CONFIDENCE,
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "status": "untested",
    }
    base.update(overrides)
    return base


def test_prior_confidence_is_max_entropy():
    assert PRIOR_CONFIDENCE == 0.5
    assert _entropy(PRIOR_CONFIDENCE) == 1.0


def test_generated_hypotheses_start_at_the_prior():
    hyps = generate_initial_hypotheses("Backend Engineer", max_hypotheses=3)
    assert hyps
    assert all(h["confidence"] == PRIOR_CONFIDENCE for h in hyps)
    assert all(h["status"] == "untested" for h in hyps)


def test_entropy_values():
    assert _entropy(0.5) == pytest.approx(1.0)
    assert _entropy(0.9) == pytest.approx(0.4690, abs=1e-3)
    assert _entropy(0.2) == pytest.approx(0.7219, abs=1e-3)
    assert _entropy(0.0) == 0.0
    assert _entropy(1.0) == 0.0


def test_expected_information_gain_scoring():
    assert expected_information_gain(_hypothesis(status="untested")) == 1.0
    assert expected_information_gain(_hypothesis(status="refuted")) == 0.0
    assert expected_information_gain(
        _hypothesis(status="confirmed", confidence=0.95)
    ) == 0.0
    assert expected_information_gain(
        _hypothesis(status="testing", confidence=0.5)
    ) == pytest.approx(1.0, abs=1e-3)
    assert expected_information_gain(
        _hypothesis(status="testing", confidence=0.2)
    ) == pytest.approx(0.7219, abs=1e-3)


def test_next_target_empty_and_all_refuted():
    assert next_target([]) is None
    assert next_target([_hypothesis(status="refuted"), _hypothesis(status="refuted")]) is None


def test_next_target_prefers_first_untested_for_coverage():
    h1 = _hypothesis(id="h1")
    h2 = _hypothesis(id="h2")
    target = next_target([h1, h2])
    assert target["id"] == "h1"
    assert target["selection_reason"] == "untested"
    assert target["information_gain"] == 1.0


def test_untested_beats_testing_even_when_close():
    untested = _hypothesis(id="u")
    testing = _hypothesis(id="t", status="testing", confidence=0.55)
    target = next_target([testing, untested])
    assert target["id"] == "u"


def test_testing_target_is_max_entropy():
    far = _hypothesis(id="far", status="testing", confidence=0.8)
    near = _hypothesis(id="near", status="testing", confidence=0.52)
    target = next_target([far, near])
    assert target["id"] == "near"
    assert target["selection_reason"] == "max_information_gain"
    assert target["information_gain"] > 0.0


def test_refuted_hypotheses_are_never_selected():
    refuted = _hypothesis(id="r", status="refuted", confidence=0.1)
    testing = _hypothesis(id="t", status="testing", confidence=0.55)
    target = next_target([refuted, testing])
    assert target["id"] == "t"


def test_saturation_confirmed_hypotheses_are_not_retargeted():
    settled = _hypothesis(id="s", status="confirmed", confidence=0.85)
    less_settled = _hypothesis(id="l", status="confirmed", confidence=0.82)
    assert next_target([settled, less_settled]) is None


def test_saturation_all_settled_returns_none_no_deep_probe():
    strong = _hypothesis(id="strong", status="confirmed", confidence=0.95)
    weaker = _hypothesis(id="weaker", status="confirmed", confidence=0.92)
    assert next_target([strong, weaker]) is None


def test_next_target_excludes_recently_probed_target():
    h1 = _hypothesis(id="h1")
    h2 = _hypothesis(id="h2")
    assert next_target([h1, h2], exclude_ids=["h1"])["id"] == "h2"


def test_next_target_saturation_when_only_recent_target_open():
    h1 = _hypothesis(id="h1")
    assert next_target([h1], exclude_ids=["h1"]) is None


def test_next_target_scopes_to_planned_competency():
    h1 = _hypothesis(id="h1", competency="tech_core")
    h2 = _hypothesis(id="h2", competency="tech_db")
    target = next_target([h1, h2], planned_competency="tech_db")
    assert target["id"] == "h2"


def test_compute_relevance_matches_evidence_competency_ids():
    from app.agents.reasoning.hypothesis_engine import compute_relevance

    # The loop bug: hypothesis statements carry the taxonomy *name* ("Scalable
    # Systems") while evidence carries the competency *id* ("tech_core") — the
    # keyword path never matched, so beliefs never updated and the same
    # hypothesis was re-targeted every turn.
    hyp = {"competency": "tech_core", "statement": "Candidate demonstrates Scalable Systems"}
    ev = {"competency": "tech_core", "dimension": "technical", "evidence_text": "vague"}
    assert compute_relevance(hyp, ev) == 0.85


def test_next_target_does_not_mutate_input():
    hyps = [_hypothesis(id="h1", status="testing", confidence=0.6)]
    original = [dict(h) for h in hyps]
    next_target(hyps)
    assert hyps == original


def test_evidence_moves_confidence_off_the_prior():
    h = _hypothesis()
    updated = update_hypotheses(
        [h],
        [{"competency": "tech_core", "dimension": "technical", "score": 9.0,
          "confidence": 0.9, "evidence_text": "Strong tech_core answer"}],
        required_evidence_map={"tech_core": 1},
    )
    assert updated[0]["confidence"] > PRIOR_CONFIDENCE
    # Fix 11: even with a blueprint minimum of 1, one record can never confirm —
    # a single read is too thin for a hiring belief.
    assert updated[0]["status"] == "testing"


def test_two_records_confirm_even_with_minimum_of_one():
    h = _hypothesis()
    evidence = [
        {"competency": "tech_core", "dimension": "technical", "score": 9.0,
         "confidence": 0.9, "evidence_text": "Strong tech_core answer"},
        {"competency": "tech_core", "dimension": "technical", "score": 8.5,
         "confidence": 0.9, "evidence_text": "Another strong tech_core answer"},
    ]
    updated = update_hypotheses(
        [h], evidence, required_evidence_map={"tech_core": 1},
    )
    assert updated[0]["status"] == "confirmed"


def test_compute_relevance_single_shared_word_is_too_weak():
    from app.agents.reasoning.hypothesis_engine import compute_relevance

    # Fix 11: one shared word (e.g. "team") used to link a claim to every
    # hypothesis mentioning it, over-settling them from a single answer.
    hyp = {"competency": "tech_core", "statement": "Candidate leads the team well"}
    ev = {"competency": "", "dimension": "communication",
          "evidence_text": "The team shipped on time"}
    assert compute_relevance(hyp, ev) == 0.1
    assert compute_relevance(hyp, ev) < 0.3


def test_compute_relevance_two_shared_words_links_with_cap():
    from app.agents.reasoning.hypothesis_engine import compute_relevance

    hyp = {"competency": "tech_core", "statement": "Candidate has strong tech_core skills"}
    ev = {"competency": "", "dimension": "technical",
          "evidence_text": "tech_core skills showed in the design"}
    assert 0.3 <= compute_relevance(hyp, ev) <= 0.6


def test_single_evidence_record_is_not_confirmed_with_default_requirement():
    """V5: confirmation needs evidence_count >= required_evidence (default 3),
    so one record only moves the hypothesis into testing."""
    h = _hypothesis()
    updated = update_hypotheses(
        [h],
        [{"competency": "tech_core", "dimension": "technical", "score": 9.0,
          "confidence": 0.9, "evidence_text": "Strong tech_core answer"}],
    )
    assert updated[0]["confidence"] > PRIOR_CONFIDENCE
    assert updated[0]["status"] == "testing"


def test_after_evidence_untested_hypothesis_is_next_coverage_target():
    probed = _hypothesis(
        id="probed", statement="Candidate has strong tech_core skills",
        status="testing", confidence=0.6,
    )
    unprobed = _hypothesis(
        id="unprobed", statement="Candidate is weak in tech_devops",
        direction="negative",
    )
    target = next_target([probed, unprobed])
    assert target["id"] == "unprobed"
    assert target["selection_reason"] == "untested"
