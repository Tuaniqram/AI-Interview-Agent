"""Plan step 2: evidence carries the competency score (not the top dimension),
and hypotheses are neutral at the hire bar (6.5)."""
import pytest

from app.agents.evaluation.scoring import (
    competency_score,
    competency_score_weights,
    primary_competency_dimension,
)
from app.agents.reasoning.evidence_engine import _supports_hypothesis
from app.agents.reasoning.hypothesis_engine import _evidence_support


def _ev(**scores):
    return {dim: {"score": s, "confidence": 0.8} for dim, s in scores.items()}


def test_fluent_but_shallow_answer_scores_on_content():
    # communication 9 carries no weight for a technical competency
    score = competency_score(_ev(technical=5.0, communication=9.0, reasoning=6.0, completeness=5.5), "technical")
    assert score == pytest.approx(0.5 * 5.0 + 0.3 * 6.0 + 0.2 * 5.5)
    assert 5.2 <= score <= 5.8


def test_competency_score_renormalizes_over_scored_dimensions():
    score = competency_score(_ev(technical=6.0, reasoning=None), "technical")
    assert score == pytest.approx(6.0)


def test_competency_score_none_when_nothing_scored():
    assert competency_score({}, "technical") is None
    assert competency_score(_ev(technical=None), "technical") is None


def test_weights_sum_to_one_per_category():
    for category in ("technical", "behavioral", "cognitive", "experience", "_domain"):
        assert sum(competency_score_weights(category).values()) == pytest.approx(1.0)


def test_primary_dimension_follows_category():
    ev = _ev(technical=5.0, behavioral=9.0, reasoning=6.0)
    assert primary_competency_dimension(ev, "technical") == "technical"
    assert primary_competency_dimension(ev, "behavioral") == "behavioral"


def test_hypothesis_neutral_at_hire_bar():
    assert _evidence_support(0.65, "positive") == pytest.approx(0.5)
    assert _evidence_support(0.85, "positive") > 0.75
    assert _evidence_support(0.40, "positive") < 0.25
    # negative hypotheses invert
    assert _evidence_support(0.85, "negative") < 0.25


def test_brain_keeps_difficulty_tracking_fields():
    from app.core.interview_brain import InterviewBrain

    brain = InterviewBrain().sync_from_dict({"max_difficulty_reached": 4, "low_windows": 2})
    assert brain.max_difficulty_reached == 4
    assert brain.low_windows == 2
    assert InterviewBrain().max_difficulty_reached is None  # falls back to difficulty_level until tracked


def test_edge_support_band():
    assert _supports_hypothesis("positive", 8.5) is True
    assert _supports_hypothesis("positive", 6.5) is True
    assert _supports_hypothesis("positive", 5.5) is None  # neutral: no edge
    assert _supports_hypothesis("positive", 4.0) is False
    assert _supports_hypothesis("negative", 8.5) is False
