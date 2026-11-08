"""Plan step 5: the claim ledger — changed figures in the candidate's own words reach the decision."""
import pytest

from app.agents.decision.decision_engine import decide_hiring_decision
from app.agents.reasoning.claim_ledger import (
    apply_claim_ledger,
    detect_conflicts,
    fold_claims,
    known_claims_brief,
    next_conflict_to_reconcile,
    parse_value,
    settle_after_reconcile,
)


@pytest.mark.parametrize("text,number,unit,is_range", [
    ("93%", 93.0, "%", False),
    ("350 ms", 0.35, "s", False),
    ("2.1 million rps", 2_100_000.0, "rps", False),
    ("4 hours", 14_400.0, "s", False),
    ("30×", 30.0, "x", False),
    ("30x faster", 30.0, "x", False),
    ("1,200 users", 1200.0, "users", False),
    ("from 120 ms to 12 ms", 0.012, "s", True),
    ("10-15%", 15.0, "%", True),
    ("no number here", None, "", False),
])
def test_parse_value(text, number, unit, is_range):
    parsed = parse_value(text)
    assert parsed.unit == unit and parsed.is_range is is_range
    assert parsed.number == (pytest.approx(number) if number is not None else None)


def _answer(state, question_number, claims=(), **extras):
    state = {
        **state,
        "question_number": question_number,
        "unified_evaluation_extras": {"claims": list(claims), **extras},
        "extracted_evidence": [{"id": f"e{question_number}", "competency": "tech_core"}],
    }
    return apply_claim_ledger(state)


def _claim(key, value):
    return {"metric_key": key, "value": value, "quote": f"it was {value}"}


def test_changed_figure_gives_one_medium_conflict_mirrored_into_contradictions():
    s = _answer({"contradictions": [{"type": "score_inconsistency", "severity": "medium"}]}, 2,
                [_claim("settlement_time_reduction", "87%")])
    assert s["claim_conflicts"] == []
    s = _answer(s, 5, [_claim("settlement_time_reduction", "92%")])
    (conflict,) = s["claim_conflicts"]
    assert conflict["kind"] == "changed_value" and conflict["severity"] == "medium"
    assert conflict["status"] == "open"
    assert conflict["first"]["question_number"] == 2 and conflict["second"]["question_number"] == 5
    assert "87%" in conflict["statement"] and "92%" in conflict["statement"]
    mirrored = [c for c in s["contradictions"] if c["type"] == "claim_conflict"]
    assert len(mirrored) == 1 and mirrored[0]["id"] == conflict["id"]
    assert any(c["type"] == "score_inconsistency" for c in s["contradictions"])  # others kept
    # re-running the same turn never duplicates
    again = _answer(s, 5, [_claim("settlement_time_reduction", "92%")])
    assert len(again["claim_conflicts"]) == 1


def test_small_percent_change_is_not_a_conflict():
    s = _answer({}, 1, [_claim("error_rate", "0.04%")])
    s = _answer(s, 3, [_claim("error_rate", "0.02%")])
    assert s["claim_conflicts"] == []


def test_small_relative_change_and_ranges_are_not_conflicts():
    s = _answer({}, 1, [_claim("p95_latency", "350 ms"), _claim("speedup", "from 120 ms to 12 ms")])
    s = _answer(s, 3, [_claim("p95_latency", "340 ms"), _claim("speedup", "from 120 ms to 30 ms")])
    assert s["claim_conflicts"] == []


def test_units_must_match_but_time_units_are_normalized():
    s = _answer({}, 1, [_claim("batch_duration", "4 hours"), _claim("users", "1200 users")])
    s = _answer(s, 2, [_claim("batch_duration", "240 minutes"), _claim("users", "1200%")])
    assert s["claim_conflicts"] == []  # 4 h == 240 min; users vs % are not comparable


def test_explicit_correction():
    s = _answer({}, 2, [_claim("cache_hit_rate", "87%")])
    s = _answer(s, 6, corrects_earlier_claim=[{"metric_key": "cache_hit_rate", "from": "87%", "to": "91%",
                                               "quote": "actually it was 91%"}])
    (conflict,) = s["claim_conflicts"]
    assert conflict["kind"] == "explicit_correction" and conflict["severity"] == "medium"


def test_bounds_conflict_only_when_broken():
    """Gate regressions (strong persona): 'sub-50 ms' then '45 ms', and '<12 ms' then '<10 ms', agree."""
    s = _answer({}, 1, [_claim("read_latency", "sub-50 ms"), _claim("write_latency_ms", "<12 ms"),
                        _claim("api_latency", "under 50 ms")])
    s = _answer(s, 11, [_claim("read_latency", "45 ms"), _claim("write_latency_ms", "<10 ms"),
                        _claim("api_latency", "80 ms")])
    assert [c["metric_key"] for c in s["claim_conflicts"]] == ["api_latency"]
    assert parse_value("at least 99%").bound == "lower" and parse_value("<12 ms").bound == "upper"


def test_corrections_need_two_differing_numbers():
    """Gate regression: 'zero evictions' -> 'hybrid LRU-LFU eviction' is not a corrected figure."""
    s = _answer({}, 9, [_claim("cache_evictions", "zero evictions"), _claim("job_time", "12 seconds")])
    s = _answer(s, 11, corrects_earlier_claim=[
        {"metric_key": "cache_evictions", "from": "zero evictions", "to": "hybrid LRU-LFU eviction"},
        {"metric_key": "job_time", "from": "12 seconds", "to": "12 s"},  # same figure: no conflict
    ])
    assert s["claim_conflicts"] == []
    s = _answer(s, 12, corrects_earlier_claim=[{"metric_key": "job_time", "from": "12 seconds", "to": "3 seconds"}])
    assert [c["kind"] for c in s["claim_conflicts"]] == ["explicit_correction"]


def test_changed_value_reported_as_correction_counts_once():
    """Gate regression: the evaluator listed 98 -> 54 both as a new value and as a correction."""
    s = _answer({}, 10, [_claim("latency_reduction_percent", "98%")])
    s = _answer(s, 11, [_claim("latency_reduction_percent", "54%")],
                corrects_earlier_claim=[{"metric_key": "latency_reduction_percent", "from": "98", "to": "54"}])
    (conflict,) = s["claim_conflicts"]
    assert conflict["kind"] == "explicit_correction"


def test_inflation_admitted_is_high_even_without_an_earlier_claim():
    s = _answer({}, 4, [_claim("board_metric", "87%")], inflation_admitted=True)
    (conflict,) = s["claim_conflicts"]
    assert conflict["kind"] == "inflation_admitted" and conflict["severity"] == "high"


def test_two_open_conflicts_raise_both_to_high():
    s = _answer({}, 1, [_claim("a_rate", "50%"), _claim("b_ms", "100 ms")])
    s = _answer(s, 3, [_claim("a_rate", "70%")])
    assert [c["severity"] for c in s["claim_conflicts"]] == ["medium"]
    s = _answer(s, 5, [_claim("b_ms", "300 ms")])
    assert [c["severity"] for c in s["claim_conflicts"]] == ["high", "high"]
    assert all(c["severity"] == "high" for c in s["contradictions"] if c["type"] == "claim_conflict")


def test_settle_after_reconcile():
    conflict = {"status": "asked", "severity": "high"}
    assert settle_after_reconcile(conflict, {"verifiable": True}) == {"status": "explained", "severity": "low"}
    assert settle_after_reconcile(conflict, {"verifiable": False})["status"] == "unexplained"
    assert settle_after_reconcile(conflict, {"verifiable": True}, created_new_conflict=True)["status"] == "unexplained"


def test_next_conflict_to_reconcile_is_the_oldest_open_one():
    conflicts = [
        {"id": "late", "status": "open", "second": {"question_number": 7}},
        {"id": "asked", "status": "asked", "second": {"question_number": 2}},
        {"id": "early", "status": "open", "second": {"question_number": 4}},
    ]
    assert next_conflict_to_reconcile(conflicts)["id"] == "early"
    assert next_conflict_to_reconcile([{"status": "explained"}]) is None


def test_known_claims_brief_lists_latest_value_per_key():
    ledger, _ = fold_claims([], [_claim("a_rate", "50%")], 1)
    ledger, _ = fold_claims(ledger, [_claim("a_rate", "70%"), _claim("b_ms", "9 ms")], 3)
    brief = known_claims_brief(ledger)
    assert "a_rate: 70% (Q3)" in brief and "b_ms: 9 ms (Q3)" in brief and "50%" not in brief
    assert known_claims_brief([]) == "None"


def test_conflicts_only_compare_with_earlier_questions():
    ledger, new = fold_claims([], [_claim("x_rate", "50%"), _claim("x_rate", "90%")], 2)
    assert detect_conflicts(ledger, new, question_number=2) == []


def test_hire_side_draft_with_one_open_conflict_needs_reconciling():
    result = decide_hiring_decision(
        holistic_score=8.5, coverage_ratio=1.0, evidence_count=12, difficulty_reached=5,
        unexplained_claim_conflicts=1,
    )
    assert result["draft_decision"] == "strong_hire"
    assert result["decision"] == "insufficient_evidence"
    assert result["adjustments"][-1]["rule"] == "claim_conflict"


def test_two_conflicts_or_inflation_cap_at_lean_no_hire():
    two = decide_hiring_decision(holistic_score=8.5, coverage_ratio=1.0, evidence_count=12,
                                 difficulty_reached=5, unexplained_claim_conflicts=2)
    inflated = decide_hiring_decision(holistic_score=5.5, coverage_ratio=1.0, evidence_count=12,
                                      difficulty_reached=5, inflation_admitted=True)
    assert two["decision"] == "lean_no_hire" and inflated["decision"] == "lean_no_hire"


def test_decision_signals_split_claim_conflicts_from_the_score_penalty():
    from app.agents.decision.hiring_decision import _decision_signals

    state = {
        "contradictions": [
            {"type": "claim_conflict", "severity": "high"},
            {"type": "score_inconsistency", "severity": "medium"},
        ],
        "claim_conflicts": [
            {"status": "open", "kind": "changed_value"},
            {"status": "explained", "kind": "changed_value"},
        ],
    }
    signals = _decision_signals(state)
    assert signals["contradiction_count"] == 1  # the score inconsistency only
    assert signals["unexplained_claim_conflicts"] == 1  # the explained one no longer counts
    assert signals["inflation_admitted"] is False


def _director_state(contradictions):
    return {
        "reflection_action": "probe", "evidence_sufficiency": {}, "question_number": 6, "max_questions": 14,
        "consecutive_probes": 0, "last_hypothesis_target_id": "", "difficulty_level": 2,
        "evaluation_score": 6.0,
        "hypothesis_target": {"id": "h1", "competency": "tech_core", "status": "testing", "confidence": 0.6},
        "contradiction_state": {"contradictions": contradictions, "needs_challenge": False},
    }


def test_director_does_not_rotate_away_from_claim_conflicts():
    from app.agents.decision.director import director_controller

    conflicts = [{"type": "claim_conflict", "severity": "high"}, {"type": "claim_conflict", "severity": "high"}]
    decision = director_controller(_director_state(conflicts))
    assert "serious contradictions" not in decision["reason"]
    # score inconsistencies still trigger the rotation
    other = [{"type": "score_inconsistency", "severity": "high"}, {"type": "score_inconsistency", "severity": "medium"}]
    rotated = director_controller(_director_state(other))
    assert rotated["action"] == "CHANGE_COMPETENCY" and "serious contradictions" in rotated["reason"]


def test_report_lists_claim_conflicts():
    from app.engine.builders import build_report_response

    report = build_report_response({
        "claim_conflicts": [{"statement": "x: 87% (Q2) vs 92% (Q5)", "metric_key": "x",
                             "first": {"question_number": 2}, "second": {"question_number": 5},
                             "kind": "changed_value", "status": "open", "severity": "medium"}],
        "answer_signals": [{"verifiable": False}, {"verifiable": True}],
    })
    assert report["claim_conflicts"][0]["questions"] == [2, 5]
    assert report["unsubstantiated_share"] == 0.5


async def test_evaluator_prompt_lists_earlier_claims(stub_llm):
    import json

    from app.agents.evaluation.candidate_evaluator import unified_evaluator_node
    from tests.conftest import EVALUATOR_JSON, make_v4_state

    stub = stub_llm(response=json.dumps(EVALUATOR_JSON))
    ledger, _ = fold_claims([], [_claim("settlement_time_reduction", "87%")], 2)
    await unified_evaluator_node(make_v4_state(
        current_question="Q", candidate_answer="A", question_objective={"target_competency": "tech_core"},
        claim_ledger=ledger,
    ))
    assert "settlement_time_reduction: 87% (Q2)" in stub.calls[0]["prompt"]
