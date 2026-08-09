"""V5 decision engine (Fix 9): deterministic 7-point hiring scale + wiring."""
from tests.conftest import make_v4_state

from app.agents.decision.decision_engine import (
    DECISION_SCALE,
    compute_decision_score,
    decide_hiring_decision,
    map_decision,
)
from app.agents.decision.decision_review import finalize_decision
from app.agents.decision.hiring_decision import _decision_signals, hiring_decision_node


def test_map_decision_uses_all_seven_points():
    assert map_decision(9.0) == "strong_hire"
    assert map_decision(8.0) == "hire"
    assert map_decision(7.0) == "lean_hire"
    assert map_decision(6.0) == "insufficient_evidence"
    assert map_decision(4.5) == "lean_no_hire"
    assert map_decision(3.0) == "no_hire"
    assert map_decision(1.0) == "strong_no_hire"


def test_decision_scale_has_seven_labels():
    assert len(DECISION_SCALE) == 7
    assert DECISION_SCALE[3] == "insufficient_evidence"


def test_compute_decision_score_anchored_on_holistic():
    assert compute_decision_score(
        holistic_score=8.0, coverage_ratio=1.0, confirmed_ratio=0.8
    ) > compute_decision_score(
        holistic_score=5.0, coverage_ratio=1.0, confirmed_ratio=0.8
    )


def test_contradictions_pull_score_toward_middle():
    clean = compute_decision_score(
        holistic_score=7.0, coverage_ratio=1.0, confirmed_ratio=0.8,
        contradiction_count=0,
    )
    conflicted = compute_decision_score(
        holistic_score=7.0, coverage_ratio=1.0, confirmed_ratio=0.8,
        contradiction_count=3,
    )
    assert conflicted < clean


def test_high_difficulty_adds_signal():
    deep = compute_decision_score(
        holistic_score=7.0, coverage_ratio=1.0, confirmed_ratio=0.8,
        difficulty_reached=5,
    )
    shallow = compute_decision_score(
        holistic_score=7.0, coverage_ratio=1.0, confirmed_ratio=0.8,
        difficulty_reached=2,
    )
    assert deep > shallow


def test_decide_hiring_decision_gates_on_evidence_count():
    result = decide_hiring_decision(
        holistic_score=9.0, coverage_ratio=1.0, confirmed_ratio=0.9,
        evidence_count=2,
    )
    assert result["decision"] == "insufficient_evidence"
    assert result["flag_review"] is True


def test_decide_hiring_decision_strong_hire():
    result = decide_hiring_decision(
        holistic_score=9.0, coverage_ratio=1.0, confirmed_ratio=0.9,
        evidence_count=8, difficulty_reached=5,
    )
    assert result["decision"] == "strong_hire"
    assert result["decision_scale"] == "7_point"
    assert result["signals"]["evidence_count"] == 8


def test_low_difficulty_caps_strong_hire():
    """D2: a candidate never pushed past difficulty 1 cannot get a strong_hire
    even with a high holistic score — evidence earned at the top of the scale
    is fully credited, at the bottom it is discounted."""
    at_top = decide_hiring_decision(
        holistic_score=8.6, coverage_ratio=0.9, confirmed_ratio=0.8,
        evidence_count=8, difficulty_reached=5,
    )
    at_bottom = decide_hiring_decision(
        holistic_score=8.6, coverage_ratio=0.9, confirmed_ratio=0.8,
        evidence_count=8, difficulty_reached=1,
    )
    assert at_top["decision"] == "strong_hire"
    assert at_bottom["decision"] != "strong_hire"
    assert at_bottom["decision"] in ("hire", "lean_hire", "insufficient_evidence")
    assert at_bottom["decision_score"] < at_top["decision_score"]


def test_decision_rationale_explains_difficulty_credit():
    result = decide_hiring_decision(
        holistic_score=8.6, coverage_ratio=0.9, confirmed_ratio=0.8,
        evidence_count=8, difficulty_reached=1,
    )
    assert "difficulty credit" in result["rationale"]
    assert "0.64" in result["rationale"]


def test_decision_signals_extract_from_state():
    state = make_v4_state(
        final_report={"holistic_score": 7.5},
        hiring_recommendation={"coverage_ratio": 0.8},
        difficulty_level=4,
        contradictions=[{"severity": "high"}, {"severity": "low"}],
        evidence_store=[{"id": "e1"}, {"id": "e2"}, {"id": "e3"}, {"id": "e4"}],
        hypotheses=[
            {"status": "confirmed"},
            {"status": "confirmed"},
            {"status": "refuted"},
        ],
    )
    signals = _decision_signals(state)
    assert signals["holistic_score"] == 7.5
    assert signals["coverage_ratio"] == 0.8
    assert signals["contradiction_count"] == 1
    assert signals["evidence_count"] == 4
    assert signals["confirmed_ratio"] == 0.5


async def test_hiring_decision_node_keeps_legacy_verdict(stub_llm):
    stub_llm(response='{"decision": "hire", "confidence": 0.8, "rationale": "r", "next_steps": []}')
    state = make_v4_state(
        final_report={"holistic_score": 8.0, "key_strengths": [], "key_weaknesses": []},
        hiring_recommendation={"verdict": "hire", "confidence": 0.8, "coverage_ratio": 0.9},
        evidence_store=[{"id": f"e{i}"} for i in range(6)],
        hypotheses=[{"status": "confirmed"} for _ in range(4)],
    )
    result = await hiring_decision_node(state)
    assert result["hiring_decision"]["decision"] in DECISION_SCALE
    # P1: the LLM explains the engine's decision — it never proposes one, so
    # a hostile or legacy llm_draft carries no decision/confidence.
    assert "decision" not in result["hiring_decision"]["llm_draft"]
    assert "confidence" not in result["hiring_decision"]["llm_draft"]
    assert result["hiring_decision"]["llm_draft"]["rationale"]
    assert result["hiring_recommendation"]["verdict"] == "hire"


def test_finalize_demotes_7_point_decision():
    draft = {
        "decision": "strong_hire",
        "confidence": 0.85,
        "rationale": "draft",
        "next_steps": [],
    }
    checks = [{"issue": "insufficient_evidence", "severity": "high", "detail": "none"}]
    final = finalize_decision(draft, checks)
    assert final["decision"] == "insufficient_evidence"
    assert final["demoted_to_undecided"] is True
