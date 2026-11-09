"""A practice candidate's chosen length is honoured; organization interviews keep the engine's cap."""
from types import SimpleNamespace

from app.api.interview_ws import _question_cap

STYLE = {"max_questions": 14}


def _session(kind, total):
    return SimpleNamespace(session_type=kind, total_questions=total)


def test_practice_uses_the_chosen_length():
    assert _question_cap(_session("practice", 5), STYLE) == 5


def test_practice_never_exceeds_the_engine_cap():
    assert _question_cap(_session("practice", 20), STYLE) == 14


def test_practice_has_a_floor_of_three():
    assert _question_cap(_session("practice", 1), STYLE) == 3


def test_practice_without_a_choice_uses_the_engine_cap():
    assert _question_cap(_session("practice", None), STYLE) == 14


def test_organization_interview_ignores_the_stored_default():
    assert _question_cap(_session("organization", 10), STYLE) == 14
