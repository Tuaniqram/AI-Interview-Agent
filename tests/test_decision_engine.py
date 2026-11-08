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
    # Plan step 3 thresholds on the competency-average scale.
    assert map_decision(8.0) == "strong_hire"
    assert map_decision(7.9) == "hire"
    assert map_decision(7.0) == "hire"
    assert map_decision(6.5) == "lean_hire"
    assert map_decision(6.2) == "lean_hire"
    assert map_decision(6.0) == "insufficient_evidence"
    assert map_decision(4.5) == "lean_no_hire"
    assert map_decision(3.0) == "no_hire"
    assert map_decision(1.0) == "strong_no_hire"


def test_decision_score_is_the_canonical_score_without_bonus_terms():
    """Plan step 3 (P1 link 2): no +coverage, +confirmed or difficulty-credit terms."""
    for coverage, confirmed, difficulty in ((1.0, 1.0, 5), (0.0, 0.0, 1), (0.5, 0.2, 3)):
        assert compute_decision_score(
            holistic_score=6.4, coverage_ratio=coverage, confirmed_ratio=confirmed,
            difficulty_reached=difficulty,
        ) == 6.4


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


def test_difficulty_caps_the_label_not_the_score():
    """P4: a candidate the engine never escalated isn't scored down, only kept off the top labels."""
    result = decide_hiring_decision(
        holistic_score=8.5, coverage_ratio=1.0, confirmed_ratio=0.8,
        evidence_count=10, difficulty_reached=2,
    )
    assert result["decision_score"] == 8.5
    assert result["draft_decision"] == "strong_hire"
    assert result["decision"] == "lean_hire"
    assert [a["rule"] for a in result["adjustments"]] == ["difficulty"]
    assert "not tested at the role's level" in result["adjustments"][0]["reason"]


def test_difficulty_cap_follows_the_role_floor():
    senior = decide_hiring_decision(
        holistic_score=7.5, coverage_ratio=1.0, evidence_count=10, difficulty_reached=3, role_floor=3,
    )
    assert senior["decision"] == "lean_hire"  # a senior role needs level 4
    junior = decide_hiring_decision(
        holistic_score=7.5, coverage_ratio=1.0, evidence_count=10, difficulty_reached=3, role_floor=1,
    )
    assert junior["decision"] == "hire"


def test_caps_never_touch_a_no_hire_side_label():
    result = decide_hiring_decision(
        holistic_score=3.0, coverage_ratio=0.2, evidence_count=10, difficulty_reached=1,
        unsubstantiated_share=0.9,
    )
    assert result["decision"] == "no_hire" and result["adjustments"] == []


def test_cap_order_table():
    from app.agents.decision.decision_engine import apply_decision_caps

    base = {"evidence_count": 10, "coverage_ratio": 1.0, "difficulty_reached": 5, "role_floor": 1,
            "unsubstantiated_share": 0.0}
    cases = [
        ({}, "strong_hire", []),
        ({"evidence_count": 3}, "insufficient_evidence", ["evidence_count"]),
        ({"coverage_ratio": 0.8}, "hire", ["coverage"]),
        # strong_hire passes through two coverage caps (< 0.85, then < 0.75 or < 0.5); each is recorded.
        ({"coverage_ratio": 0.6}, "lean_hire", ["coverage", "coverage"]),
        ({"coverage_ratio": 0.4}, "insufficient_evidence", ["coverage", "coverage"]),
        ({"difficulty_reached": 2}, "lean_hire", ["difficulty"]),
        ({"coverage_ratio": 0.8, "difficulty_reached": 2}, "lean_hire", ["coverage", "difficulty"]),
        ({"unsubstantiated_share": 0.5}, "insufficient_evidence", ["unsubstantiated"]),
        ({"unsubstantiated_share": 0.49}, "strong_hire", []),
    ]
    for overrides, expected, rules in cases:
        decision, adjustments = apply_decision_caps("strong_hire", {**base, **overrides})
        assert decision == expected, overrides
        assert [a["rule"] for a in adjustments] == rules, overrides
        for a in adjustments:
            assert set(a) == {"rule", "from", "to", "reason"} and a["reason"]


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
    assert at_bottom["decision"] == "lean_hire"
    # The score is the evidence; difficulty only caps the label (plan step 3).
    assert at_bottom["decision_score"] == at_top["decision_score"]


def test_decision_rationale_explains_the_cap():
    result = decide_hiring_decision(
        holistic_score=8.6, coverage_ratio=0.9, confirmed_ratio=0.8,
        evidence_count=8, difficulty_reached=1,
    )
    assert "Capped strong_hire -> lean_hire" in result["rationale"]
    assert "difficulty reached 1 < 3" in result["rationale"]


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
    # N4: the same resolved-hypothesis ratio the sufficiency layer uses (2 confirmed of 3 tested).
    assert round(signals["confirmed_ratio"], 3) == 0.667
    assert signals["role_floor"] == 1
    assert signals["unsubstantiated_share"] is None


async def test_hiring_decision_node_is_deterministic_and_keeps_legacy_verdict(stub_llm):
    stub = stub_llm(response='{"decision": "hire", "confidence": 0.8, "rationale": "r", "next_steps": []}')
    state = make_v4_state(
        final_report={"holistic_score": 8.0, "key_strengths": [], "key_weaknesses": []},
        hiring_recommendation={"verdict": "hire", "confidence": 0.8, "coverage_ratio": 0.9},
        evidence_store=[{"id": f"e{i}"} for i in range(6)],
        hypotheses=[{"status": "confirmed"} for _ in range(4)],
    )
    result = await hiring_decision_node(state)
    assert stub.calls == []  # plan step 3: no LLM in the decision
    hd = result["hiring_decision"]
    assert hd["decision"] in DECISION_SCALE
    assert hd["draft_decision"] == "strong_hire"
    assert "llm_draft" not in hd
    assert result["hiring_recommendation"]["verdict"] == "hire"


async def test_explain_final_decision_explains_never_decides(stub_llm):
    from app.agents.decision.hiring_decision import explain_final_decision

    stub = stub_llm(response='{"decision": "strong_hire", "rationale": "Capped for difficulty.", "next_steps": ["x"]}')
    state = make_v4_state(hiring_decision={
        "decision": "lean_hire", "draft_decision": "strong_hire", "decision_score": 8.5,
        "adjustments": [{"rule": "difficulty", "from": "strong_hire", "to": "lean_hire", "reason": "level 2"}],
        "next_steps": ["schedule a focused reference check"],
    })
    result = await explain_final_decision(state)
    hd = result["hiring_decision"]
    assert hd["decision"] == "lean_hire"  # unchanged
    assert hd["llm_draft"] == {"rationale": "Capped for difficulty."}
    prompt = stub.calls[0]["prompt"]
    assert "lean_hire" in prompt and "strong_hire" in prompt and "level 2" in prompt


async def test_explain_final_decision_falls_back_on_llm_failure(stub_llm):
    from app.agents.decision.hiring_decision import explain_final_decision

    stub_llm(fail=True)
    state = make_v4_state(hiring_decision={
        "decision": "insufficient_evidence", "draft_decision": "hire", "decision_score": 7.2,
        "adjustments": [{"rule": "review:missing_competency", "from": "hire", "to": "insufficient_evidence",
                         "reason": "coverage 40%"}],
    })
    result = await explain_final_decision(state)
    assert "coverage 40%" in result["hiring_decision"]["llm_draft"]["rationale"]


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
    assert final["adjustments"] == [{
        "rule": "review:insufficient_evidence", "from": "strong_hire", "to": "insufficient_evidence",
        "reason": "none",
    }]
    assert final["demotion_reason"] == "none"
