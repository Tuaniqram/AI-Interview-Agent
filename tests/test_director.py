"""Director decision-controller tests — the four-action internal routing."""
import pytest

from app.agents.decision.director import (
    DIRECTOR_ACTIONS,
    MAX_CONSECUTIVE_PROBES,
    director_controller,
)


def _state(**overrides):
    state = {
        "reflection_action": "probe",
        "evidence_sufficiency": {"is_sufficient": False},
        "contradictions": [],
        "question_number": 3,
        "max_questions": 14,
        "hypothesis_target": {
            "id": "h1",
            "status": "testing",
            "confidence": 0.4,
        },
        "consecutive_probes": 0,
        "last_hypothesis_target_id": "",
    }
    state.update(overrides)
    return state


def test_director_actions_vocabulary():
    assert set(DIRECTOR_ACTIONS) == {"CONTINUE", "PROBE", "CHANGE_COMPETENCY", "FINISH"}


def test_director_continues_on_open_state():
    decision = director_controller(_state())
    assert decision["action"] == "CONTINUE"
    assert decision["reason"]


def test_director_finishes_when_evidence_sufficient():
    decision = director_controller(_state(
        evidence_sufficiency={"is_sufficient": True, "coverage_ratio": 0.9},
        question_number=6,
    ))
    assert decision["action"] == "FINISH"


def test_director_does_not_finish_with_covered_ratio_but_starved_required_competency():
    """P2: coverage may be 'sufficient' by ratio while a required competency
    still has too little evidence — the director must keep probing."""
    decision = director_controller(_state(
        evidence_sufficiency={"is_sufficient": True, "coverage_ratio": 0.73},
        question_number=6,
        competency_summary={
            "problem_solvin": {"evidence_count": 3, "average_score": 8.0, "gap": 0.0},
            "communication": {"evidence_count": 2, "average_score": 8.0, "gap": 0.0},
            "system_design": {"evidence_count": 1, "average_score": 8.0, "gap": 0.5},
        },
        required_competencies=["problem_solvin", "communication", "system_design"],
        hypotheses=[{"id": "h1", "competency": "system_design", "status": "untested"}],
    ))
    assert decision["action"] == "CONTINUE"
    assert "evidence gaps" in decision["reason"]


def test_director_finishes_when_required_competencies_fully_covered():
    """P2: the same sufficiency signal finishes once every required competency
    has its minimum evidence and no required hypothesis is untested."""
    decision = director_controller(_state(
        evidence_sufficiency={"is_sufficient": True, "coverage_ratio": 0.9},
        question_number=6,
        competency_summary={
            "problem_solvin": {"evidence_count": 3, "average_score": 8.0, "gap": 0.0},
            "communication": {"evidence_count": 2, "average_score": 8.0, "gap": 0.0},
            "system_design": {"evidence_count": 2, "average_score": 8.0, "gap": 0.0},
        },
        required_competencies=["problem_solvin", "communication", "system_design"],
        hypotheses=[{"id": "h1", "competency": "system_design", "status": "confirmed"}],
    ))
    assert decision["action"] == "FINISH"


def test_director_keeps_probing_below_minimum_question_count():
    decision = director_controller(_state(
        reflection_action="finish",
        evidence_sufficiency={"is_sufficient": True, "coverage_ratio": 0.9},
        question_number=4,
    ))
    assert decision["action"] == "CONTINUE"
    assert decision["reason"] == (
        "below minimum question count (5) — keep probing"
    )


def test_director_finishes_when_reflection_finishes():
    decision = director_controller(_state(
        reflection_action="finish",
        question_number=6,
    ))
    assert decision["action"] == "FINISH"


def test_director_finishes_when_question_budget_exhausted():
    decision = director_controller(_state(
        question_number=14, max_questions=14, reflection_action="probe",
    ))
    assert decision["action"] == "FINISH"


def test_director_rotates_on_reflection_change_competency():
    decision = director_controller(_state(reflection_action="change_competency"))
    assert decision["action"] == "CHANGE_COMPETENCY"


def test_director_rotates_on_two_serious_contradictions():
    contradictions = [
        {"severity": "high", "type": "score_inconsistency"},
        {"severity": "medium", "type": "score_inconsistency"},
    ]
    decision = director_controller(_state(contradictions=contradictions))
    assert decision["action"] == "CHANGE_COMPETENCY"


def test_director_loop_guard_rotates_after_max_consecutive_probes():
    decision = director_controller(_state(
        consecutive_probes=MAX_CONSECUTIVE_PROBES,
        last_hypothesis_target_id="h1",
        hypothesis_target={"id": "h1", "status": "testing", "confidence": 0.5},
    ))
    assert decision["action"] == "CHANGE_COMPETENCY"


def test_director_loop_guard_does_not_rotate_on_new_target():
    decision = director_controller(_state(
        consecutive_probes=MAX_CONSECUTIVE_PROBES,
        last_hypothesis_target_id="h1",
        hypothesis_target={"id": "h2", "status": "testing", "confidence": 0.5},
    ))
    assert decision["action"] in ("CONTINUE", "PROBE")


def test_director_probes_established_belief_for_counter_evidence():
    decision = director_controller(_state(
        hypothesis_target={"id": "h1", "status": "confirmed", "confidence": 0.85},
    ))
    assert decision["action"] == "PROBE"
    assert decision["target_id"] == "h1"


def test_director_ignores_low_severity_contradictions():
    contradictions = [
        {"severity": "low", "type": "score_inconsistency"},
        {"severity": "low", "type": "score_inconsistency"},
    ]
    decision = director_controller(_state(contradictions=contradictions))
    assert decision["action"] != "CHANGE_COMPETENCY"
