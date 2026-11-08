"""Plan step 6: ask the candidate, neutrally, how two figures for the same thing fit together."""
import json

from app.agents.decision.director import director_controller
from app.agents.generation.question_generator import (
    _reconcile_fallback,
    _resolve_interview_mode,
    question_generator_node,
)
from app.agents.reasoning.claim_ledger import apply_claim_ledger
from tests.conftest import CONDUCTOR_TURN_JSON, make_v4_state

ACCUSING = ("contradict", "inconsistent", "you said something different")


def _conflict(status="open", cid="c1", second_q=5, competency="tech_system_design"):
    return {
        "id": cid, "type": "claim_conflict", "metric_key": "settlement_time_reduction",
        "first": {"question_number": 2, "value_text": "87%"},
        "second": {"question_number": second_q, "value_text": "92%"},
        "kind": "changed_value", "severity": "medium", "status": status, "asked_in_question": None,
        "statement": "settlement_time_reduction: 87% (Q2) vs 92% (Q5)", "competency": competency,
    }


def _director_state(**overrides):
    state = {
        "reflection_action": "probe", "evidence_sufficiency": {}, "question_number": 6, "max_questions": 14,
        "consecutive_probes": 0, "last_hypothesis_target_id": "", "difficulty_level": 2, "evaluation_score": 6.0,
        "hypothesis_target": {"id": "h1", "competency": "tech_core", "status": "testing", "confidence": 0.6},
        "contradiction_state": {"contradictions": [], "needs_challenge": False},
    }
    state.update(overrides)
    return state


def test_open_conflict_gives_probe_reconcile_claim():
    decision = director_controller(_director_state(claim_conflicts=[_conflict()]))
    assert decision["action"] == "PROBE"
    assert decision["probe_mode"] == "reconcile_claim"
    assert "settlement_time_reduction" in decision["reason"]


def test_asked_conflict_is_not_asked_again():
    decision = director_controller(_director_state(claim_conflicts=[_conflict(status="asked")]))
    assert decision["probe_mode"] != "reconcile_claim"


def test_reconcile_beats_the_seniority_challenge_and_the_strategy_mode():
    state = _director_state(
        claim_conflicts=[_conflict()],
        contradiction_state={"contradictions": [], "needs_challenge": True},
    )
    decision = director_controller(state)
    assert decision["probe_mode"] == "reconcile_claim"
    mode = _resolve_interview_mode({
        "question_number": 6,
        "director": decision, "claim_conflicts": [_conflict()],
        "question_strategy": {"question_strategy": {"mode": "challenge"}},
    }, claims=["cut latency by 92%"], followup_number=2)
    assert mode == "RECONCILER"


def test_reconcile_mode_needs_an_open_conflict():
    mode = _resolve_interview_mode({
        "director": {"probe_mode": "reconcile_claim"}, "claim_conflicts": [_conflict(status="asked")],
    })
    assert mode != "RECONCILER"


def test_fallback_question_names_both_figures_and_stays_neutral():
    text = _reconcile_fallback(_conflict())
    assert "87%" in text and "92%" in text
    assert not any(word in text.lower() for word in ACCUSING)


async def test_generator_asks_marks_asked_and_targets_the_claims_competency(stub_llm):
    stub = stub_llm(response=CONDUCTOR_TURN_JSON)
    state = make_v4_state(
        persona="conductor", question_number=6,
        director={"action": "PROBE", "probe_mode": "reconcile_claim"},
        claim_conflicts=[_conflict()],
        contradictions=[{"type": "claim_conflict", "id": "c1", "severity": "medium", "status": "open"}],
        hypothesis_target={"id": "h1", "competency": "tech_core", "status": "testing"},
    )
    out = await question_generator_node(state)
    assert out["interview_mode"] == "RECONCILER"
    assert out["question_objective"]["target_competency"] == "tech_system_design"
    assert out["question_objective"]["conflict_id"] == "c1"
    (conflict,) = out["claim_conflicts"]
    assert conflict["status"] == "asked" and conflict["asked_in_question"] == 7
    assert [c["status"] for c in out["contradictions"] if c["type"] == "claim_conflict"] == ["asked"]
    prompt = stub.calls[0]["prompt"]
    assert "settlement_time_reduction: 87% (question 2) vs 92% (question 5)" in prompt
    assert "{{" not in prompt


async def test_generator_llm_failure_uses_the_neutral_fallback(stub_llm):
    stub_llm(fail=True)
    out = await question_generator_node(make_v4_state(
        persona="conductor", question_number=6,
        director={"action": "PROBE", "probe_mode": "reconcile_claim"},
        claim_conflicts=[_conflict()],
    ))
    assert "87%" in out["current_question"] and "92%" in out["current_question"]


def _reconcile_answer(verifiable=True, claims=(), unsupported=()):
    return {
        "question_number": 7,
        "claim_conflicts": [{**_conflict(status="asked"), "asked_in_question": 7}],
        "claim_ledger": [
            {"metric_key": "settlement_time_reduction", "value_text": "87%", "number": 87.0, "unit": "%",
             "range": False, "bound": None, "question_number": 2},
            {"metric_key": "settlement_time_reduction", "value_text": "92%", "number": 92.0, "unit": "%",
             "range": False, "bound": None, "question_number": 5},
        ],
        "answer_signals": [{"question_number": 7, "verifiable": verifiable, "unsupported_claims": list(unsupported)}],
        "unified_evaluation_extras": {"claims": list(claims)},
        "extracted_evidence": [{"id": "e7", "competency": "tech_system_design"}],
    }


def test_substantiated_reply_explains_the_conflict():
    # restating both figures under the same key is the explanation, not a new conflict
    out = apply_claim_ledger(_reconcile_answer(claims=[
        {"metric_key": "settlement_time_reduction", "value": "87%", "quote": "87% was the p50"},
    ]))
    (conflict,) = out["claim_conflicts"]
    assert conflict["status"] == "explained" and conflict["severity"] == "low"


def test_unsubstantiated_reply_leaves_it_unexplained():
    out = apply_claim_ledger(_reconcile_answer(verifiable=False))
    (conflict,) = out["claim_conflicts"]
    assert conflict["status"] == "unexplained"


def test_explained_conflict_no_longer_caps_the_verdict():
    from app.agents.decision.hiring_decision import _decision_signals

    signals = _decision_signals({"claim_conflicts": [{**_conflict(status="explained"), "severity": "low"}]})
    assert signals["unexplained_claim_conflicts"] == 0


def test_prompt_renders_the_new_variables():
    from app.agents.generation.question_generator import _question_prompt_vars
    from app.services.prompt_loader import load_prompt

    variables = _question_prompt_vars(
        job_role="Dev", target_competency="tech_core", phase="technical", difficulty=2, persona="conductor",
        hypothesis="", competency_info="", approach="", followup_number=0, question_number=3,
        total_questions=14, conversation_history=[], candidate_profile={},
        interview_mode="RECONCILER", conflict_to_reconcile="x: 1 (question 2) vs 2 (question 4)",
    )
    prompt = load_prompt("interview", "question_generation.md", **variables)
    assert "{{" not in prompt
    assert "**Claim To Reconcile**: x: 1 (question 2) vs 2 (question 4)" in prompt
    assert "**Admitted Gap On Last Answer**: no" in prompt
    json.dumps(variables)  # plain data


def test_reconcile_comes_before_the_reflections_rotate_and_finish_signals():
    """Step 6 gate regression: the reflection said change_competency on nearly every turn, so no conflict was
    ever asked. Only the question budget comes first."""
    for reflection_action in ("change_competency", "finish"):
        decision = director_controller(_director_state(
            claim_conflicts=[_conflict()], reflection_action=reflection_action,
            evidence_sufficiency={"is_sufficient": True},
        ))
        assert decision["probe_mode"] == "reconcile_claim", reflection_action
    at_budget = director_controller(_director_state(claim_conflicts=[_conflict()], question_number=14))
    assert at_budget["action"] == "FINISH"


def test_reflection_does_not_rotate_on_claim_conflicts():
    from app.agents.reasoning.contradiction_engine import decide_next_action

    two_conflicts = [{"type": "claim_conflict", "severity": "high"}, {"type": "claim_conflict", "severity": "high"}]
    action = decide_next_action(
        competency_summary={}, required_competencies=[], evidence_sufficiency={},
        contradictions=two_conflicts, question_number=6, hypotheses=[{"status": "testing"}],
    )
    assert action != "change_competency"


def test_reply_with_new_unsupported_claims_stays_unexplained():
    """Step 6 gate: the bluffer 'explained' each conflict with a new, unbacked measurement story."""
    out = apply_claim_ledger(_reconcile_answer(unsupported=["200,000 unit tests in six weeks"]))
    assert out["claim_conflicts"][0]["status"] == "unexplained"


def test_admitted_inflation_is_never_asked_about_or_explained():
    from app.agents.reasoning.claim_ledger import next_conflict_to_reconcile, settle_after_reconcile

    inflated = {**_conflict(), "kind": "inflation_admitted"}
    assert next_conflict_to_reconcile([inflated]) is None
    assert settle_after_reconcile(inflated, {"verifiable": True})["status"] == "unexplained"


async def test_reconcile_question_without_both_figures_is_replaced(stub_llm):
    vague = json.dumps({"acknowledgement": "", "bridge": "",
                        "question": "Can you walk me through how those two figures relate to each other?"})
    stub_llm(response=vague)
    out = await question_generator_node(make_v4_state(
        persona="conductor", question_number=6,
        director={"action": "PROBE", "probe_mode": "reconcile_claim"},
        claim_conflicts=[_conflict()],
    ))
    assert "87%" in out["current_question"] and "92%" in out["current_question"]
    assert out["conversation_turn"]["question"] == out["current_question"]


def test_names_both_figures():
    from app.agents.generation.question_generator import _names_both_figures

    c = _conflict()
    assert _names_both_figures("Earlier 87%, later 92% — how do they relate?", c)
    assert not _names_both_figures("Earlier 87%, later 18% — how do they relate?", c)
    assert not _names_both_figures("How do those two figures relate?", c)


def test_three_changed_figures_hold_a_hire_even_when_explained():
    """User decision after step 6: 1-2 explained conflicts never count; 3+ changed figures need a probe round."""
    from app.agents.decision.decision_engine import decide_hiring_decision
    from app.agents.decision.hiring_decision import _decision_signals

    explained = [{**_conflict(cid=f"c{i}", status="explained"), "severity": "low"} for i in range(3)]
    signals = _decision_signals({"claim_conflicts": explained})
    assert signals["unexplained_claim_conflicts"] == 0 and signals["claim_conflicts_total"] == 3
    base = dict(holistic_score=6.4, coverage_ratio=1.0, evidence_count=12, difficulty_reached=5)
    held = decide_hiring_decision(**base, claim_conflicts_total=3)
    assert held["draft_decision"] == "lean_hire" and held["decision"] == "insufficient_evidence"
    assert held["adjustments"][-1]["rule"] == "claim_pattern"
    two = decide_hiring_decision(**base, claim_conflicts_total=2)
    assert two["decision"] == "lean_hire" and two["adjustments"] == []
    # never touches a no-hire-side label
    low = decide_hiring_decision(**{**base, "holistic_score": 4.5}, claim_conflicts_total=5)
    assert low["decision"] == "lean_no_hire" and low["adjustments"] == []


def test_admitted_inflation_is_not_counted_in_the_pattern():
    from app.agents.decision.hiring_decision import _decision_signals

    conflicts = [{**_conflict(cid="a", status="explained")}, {**_conflict(cid="b"), "kind": "inflation_admitted"}]
    assert _decision_signals({"claim_conflicts": conflicts})["claim_conflicts_total"] == 1
