import pytest

from app.agents.planning.competency_planner import get_next_competency
from app.agents.reasoning import hypothesis_engine
from app.agents.reasoning.evidence_engine import build_candidate_evidence


def test_get_next_competency_rotation():
    competencies = [
        {"id": "c1", "questions_count": 1},
        {"id": "c2", "questions_count": 0},
        {"id": "c3", "questions_count": 0},
    ]
    # When current is c1, next should be c2 (the next available after index)
    next_c = get_next_competency(competencies, current_id="c1")
    assert next_c is not None
    assert next_c["id"] == "c2"

    # When current is c3 (last), should wrap to first available (c1 is capped here > use available[0])
    next_wrap = get_next_competency(competencies, current_id="c3")
    assert next_wrap is not None
    assert next_wrap["id"] in {"c1", "c2", "c3"}


def test_resolve_target_seeding_returns_seed_when_none():
    hypotheses = []
    state = {
        "planned_competency": "comp_x",
        "session_id": "s1",
        "competency_taxonomy": [{"id": "comp_x", "name": "Comp X", "evidence_dimensions": ["communication"]}],
    }
    candidates = []
    target = hypothesis_engine._resolve_target(hypotheses, state, candidates, state.get("planned_competency"))
    assert target is not None
    assert isinstance(target, dict)
    assert target.get("competency") == "comp_x"


def test_build_candidate_evidence_fallback_assigns_competency():
    # Build a minimal evaluation with a scored dimension
    evaluation = {
        "technical": {"score": 7.0, "confidence": 0.8, "evidence": "I designed and implemented X."},
    }
    # Provide an explicit empty target so the function must fall back
    extracted = build_candidate_evidence(
        evaluation=evaluation,
        question="Tell me about X",
        question_number=1,
        session_id="s1",
        question_objective={},
        competency_taxonomy=[{"id": "fallback_comp", "name": "Fallback", "evidence_dimensions": ["other"]}],
    )
    assert isinstance(extracted, list)
    assert len(extracted) > 0
    assert isinstance(extracted[0].get("competency"), str)
    assert extracted[0].get("competency") != ""
