"""Evidence Reading V5 — semantic read of raw answers.

Covers the downgrade-only override (the core safety invariant), the
deterministic mapper, the decision-review integration (flag/trim, never
demote), and the LLM-failure fallback for the async node.
"""
import json

from app.agents.reasoning.evidence_reading import (
    effective_claim,
    evidence_reading_checks,
    evidence_reading_risk_flags,
    map_evidence_reading,
    transcript_by_question,
)
from app.brain.evidence_reasoner import classify_claim, evidence_summary_stats
from app.agents.decision.decision_review import finalize_decision, review_decision
from tests.conftest import make_v4_state

EVIDENCE_READING_JSON = json.dumps({
    "per_answer": [
        {
            "question_number": 1,
            "claim_classification": "proven",
            "specificity": "high",
            "ownership": "first_person",
            "supporting_metric": "cut p99 latency 800ms -> 120ms across 40k req/s",
            "quote": "I owned the event pipeline.",
        }
    ],
    "off_rubric": {
        "red_flags": ["overstated ownership on the caching work"],
        "hidden_strengths": ["spontaneous architecture tradeoff thinking"],
    },
    "semantic_risks": ["says led X in Q3, says had no role in X in Q8"],
})

# A regex-proven record (first-person + high complexity) with no real specifics
# — the exact case the semantic layer should downgrade.
VAGUE_PROVEN = {
    "id": "e1",
    "evidence_text": (
        "I architected the system and we reduced latency a lot across millions "
        "of users and saved costs with many optimizations and deep queues and "
        "caches and retries and more stuff"
    ),
    "ownership": "first_person",
    "complexity": "high",
}


def test_effective_claim_downgrade_only():
    assert effective_claim("proven", "proven") == "proven"
    assert effective_claim("demonstrated", "demonstrated") == "demonstrated"
    assert effective_claim("mentioned", "mentioned") == "mentioned"
    # LLM catches vagueness the regex missed -> downgrade.
    assert effective_claim("mentioned", "proven") == "mentioned"
    assert effective_claim("mentioned", "demonstrated") == "mentioned"
    # LLM can never inflate past the deterministic floor.
    assert effective_claim("proven", "mentioned") == "mentioned"
    assert effective_claim("proven", "demonstrated") == "demonstrated"
    # Missing/unknown values fall back to the floor.
    assert effective_claim(None, "proven") == "mentioned"
    assert effective_claim("proven", None) == "mentioned"


def test_semantic_override_downgrades_regex_proven():
    assert classify_claim(VAGUE_PROVEN) == "proven"
    assert classify_claim(VAGUE_PROVEN, "mentioned") == "mentioned"

    reading = {"per_answer": {"e1": {"claim_classification": "mentioned"}}}
    stats = evidence_summary_stats([VAGUE_PROVEN], evidence_reading=reading)
    assert stats["proven"] == 0
    assert stats["mentioned"] == 1
    assert stats["proof_ratio"] == 0.0
    # Without the reading, the deterministic regex path is unchanged.
    assert evidence_summary_stats([VAGUE_PROVEN])["proof_ratio"] == 1.0


def test_semantic_override_corroborates_proven():
    record = {
        "id": "e1",
        "evidence_text": "I owned the Kafka pipeline; p99 went from 800ms to 120ms.",
        "ownership": "first_person",
        "complexity": "high",
    }
    reading = {"per_answer": {"e1": {"claim_classification": "proven"}}}
    stats = evidence_summary_stats([record], evidence_reading=reading)
    assert stats["proven"] == 1
    assert stats["proof_ratio"] == 1.0


def test_map_evidence_reading_normalizes_and_drops_unknown_ids():
    store = [
        {"id": "e1", "evidence_text": "a"},
        {"id": "e2", "evidence_text": "b"},
    ]
    out = map_evidence_reading(store, {
        "per_answer": [
            {"evidence_id": "e1", "claim_classification": "proven", "verifiable": True,
             "specificity": "high", "ownership": "first_person",
             "supporting_metric": "metric", "quote": "q"},
            # Hallucinated id -> dropped, can never enter the brain.
            {"evidence_id": "ghost", "claim_classification": "proven", "verifiable": True,
             "specificity": "high", "ownership": "first_person", "supporting_metric": "", "quote": ""},
        ],
        "off_rubric": {"red_flags": ["flag"], "hidden_strengths": ["strength"]},
        "semantic_risks": ["risk"],
    })
    assert list(out["per_answer"].keys()) == ["e1"]
    assert out["per_answer"]["e1"]["claim_classification"] == "proven"
    assert out["off_rubric"]["red_flags"] == ["flag"]
    assert out["off_rubric"]["hidden_strengths"] == ["strength"]
    assert out["semantic_risks"] == ["risk"]


def test_map_evidence_reading_defaults_invalid_enum():
    out = map_evidence_reading([{"id": "e1", "evidence_text": "a"}], {
        "per_answer": [{"evidence_id": "e1", "claim_classification": "legendary",
                        "specificity": "max", "ownership": "god"}],
    })
    entry = out["per_answer"]["e1"]
    assert entry["claim_classification"] == "mentioned"
    assert "verifiable" not in entry  # plan step 7: verifiability comes from the evaluator
    assert entry["specificity"] == "low"
    assert entry["ownership"] == "vague"


def test_per_question_entries_fan_out_and_invented_questions_are_dropped():
    store = [
        {"id": "e1", "question_number": 3}, {"id": "e2", "question_number": 3}, {"id": "e3", "question_number": 4},
    ]
    out = map_evidence_reading(store, {"per_answer": [
        {"question_number": 3, "claim_classification": "demonstrated", "specificity": "medium"},
        {"question_number": 16, "claim_classification": "proven"},  # the reader cited "Q16" in a 14-question run
    ]})
    assert set(out["per_answer"]) == {"e1", "e2"}
    assert out["per_answer"]["e2"]["claim_classification"] == "demonstrated"
    assert list(out["per_question"]) == [3]


def test_risk_flags_and_checks_capped_at_medium():
    reading = {
        "off_rubric": {"red_flags": ["overstated ownership"], "hidden_strengths": []},
        "semantic_risks": ["Q3 vs Q8 mismatch"],
        "per_answer": {},
    }
    flags = evidence_reading_risk_flags(reading)
    assert any("off-rubric flag" in f for f in flags)
    assert any("cross-answer risk" in f for f in flags)

    checks = evidence_reading_checks(reading)
    assert checks
    assert all(c["severity"] == "medium" for c in checks), checks
    assert not any(c.get("demote_hire") for c in checks)
    assert not any(c["issue"] == "unverifiable_claims" for c in checks)


def _long_interview(n=14, answer_len=5000):
    questions = [{"text": f"Question {i} about topic {i}?"} for i in range(1, n + 1)]
    history = []
    for i, q in enumerate(questions, 1):
        history += [{"role": "assistant", "content": q["text"]},
                    {"role": "user", "content": f"A{i}-start " + "x" * answer_len + f" A{i}-end"}]
    evidence = [{"id": f"e{i}", "question_number": i, "evidence_text": f"quote {i}"} for i in range(1, n + 1)]
    return {"questions_asked": questions, "conversation_history": history, "evidence_store": evidence}


def test_transcript_by_question_keeps_every_question_within_the_cap():
    items = transcript_by_question(_long_interview())
    assert [i["question_number"] for i in items] == list(range(1, 15))
    total = sum(len(i["answer"]) + len(i["question"]) for i in items)
    assert total <= 24_000
    for i in items:
        n = i["question_number"]
        # trimmed in the middle: both ends survive
        assert i["answer"].startswith(f"A{n}-start") and i["answer"].endswith(f"A{n}-end")
        assert i["evidence_ids"] == [f"e{n}"]


def test_transcript_by_question_uses_raw_answers_and_keeps_short_ones_whole():
    state = _long_interview(n=3, answer_len=50)
    items = transcript_by_question(state)
    assert all("…" not in i["answer"] for i in items)
    assert items[0]["question"] == "Question 1 about topic 1?"
    # a clarification exchange stays inside its question
    state["conversation_history"][2:2] = [
        {"role": "user", "content": "Do you mean the cache?"},
        {"role": "assistant", "content": "Yes, the read cache."},
    ]
    items = transcript_by_question(state)
    assert "Do you mean the cache?" in items[0]["answer"] and items[1]["question_number"] == 2


def test_transcript_falls_back_to_the_evidence_quote_without_history():
    items = transcript_by_question({"evidence_store": [{"id": "e1", "question_number": 2, "evidence_text": "q2"}]})
    assert items == [{"question_number": 2, "question": "", "answer": "q2", "evidence_ids": ["e1"]}]


async def test_evidence_reading_node_populates_state(stub_llm):
    stub = stub_llm(response=EVIDENCE_READING_JSON)
    from app.agents.evaluation.evidence_reading import evidence_reading_node

    state = make_v4_state(
        job_role="Backend Engineer",
        evidence_store=[{"id": "e1", "question_number": 1, "evidence_text": "I owned the event pipeline."}],
        questions_asked=[{"text": "What did you own?"}],
        conversation_history=[{"role": "assistant", "content": "What did you own?"},
                              {"role": "user", "content": "I owned the event pipeline end to end."}],
    )
    out = await evidence_reading_node(state)
    assert out["evidence_reading"]["per_answer"]["e1"]["claim_classification"] == "proven"
    assert stub.calls[0]["tier"] == "strong"
    assert stub.calls[0]["temperature"] == 0.0
    prompt = stub.calls[0]["prompt"]
    assert "Evidence Reading" in prompt and "I owned the event pipeline end to end." in prompt


async def test_evidence_reading_node_falls_back_on_llm_failure(stub_llm):
    stub = stub_llm(fail=True)
    from app.agents.evaluation.evidence_reading import evidence_reading_node

    state = make_v4_state(evidence_store=[{"id": "e1", "evidence_text": "hi"}])
    out = await evidence_reading_node(state)
    assert out == state
    assert "evidence_reading" not in out


async def test_evidence_reading_node_skips_empty_evidence(stub_llm):
    stub = stub_llm(response=EVIDENCE_READING_JSON)
    from app.agents.evaluation.evidence_reading import evidence_reading_node

    out = await evidence_reading_node(make_v4_state())
    assert "evidence_reading" not in out
    assert stub.calls == []


def test_decision_review_semantic_checks_flag_but_never_demote():
    state = make_v4_state(
        hiring_decision={"decision": "hire", "decision_score": 8.0, "confidence": 0.7},
        hiring_recommendation={"verdict": "hire", "coverage_ratio": 0.9},
        evidence_store=[{"strength": 0.8} for _ in range(4)],
        evidence_reading={
            "off_rubric": {"red_flags": ["overstated ownership"], "hidden_strengths": []},
            "semantic_risks": ["Q3 vs Q8 mismatch", "zero writes vs 0.5% anomalies"],
            "per_answer": {},
        },
    )
    draft = state["hiring_decision"]
    checks = review_decision(draft, state)
    assert any(c["issue"] == "cross_answer_risk" for c in checks)

    final = finalize_decision(draft, checks, state)
    # Plan step 7: two cross-answer risks flag for review and trim confidence, never demote.
    assert final["decision"] == "hire"
    assert final["flag_review"] is True
    assert final["confidence"] < 0.7
    assert final.get("adjustments", []) == []


def test_decision_review_without_reading_is_unchanged():
    state = make_v4_state(
        hiring_decision={"decision": "hire", "decision_score": 8.0, "confidence": 0.7},
        hiring_recommendation={"verdict": "hire", "coverage_ratio": 0.9},
        evidence_store=[{"strength": 0.8} for _ in range(4)],
    )
    draft = state["hiring_decision"]
    checks = review_decision(draft, state)
    assert not any(c["issue"] in ("off_rubric_flag", "cross_answer_risk") for c in checks)
    final = finalize_decision(draft, checks, state)
    assert final["decision"] == "hire"
    assert final["flag_review"] is False
    assert final["confidence"] == 0.7


# --- flag_review truth table (plan step 7, P11) ------------------------------------------------------


def _flag(adjustments=(), checks=(), **state):
    from app.agents.decision.decision_review import compute_flag_review

    return compute_flag_review({"adjustments": list(adjustments)}, list(checks), state)


def test_flag_review_truth_table():
    assert _flag() is False
    # coverage caps alone don't need a human
    assert _flag(adjustments=[{"rule": "coverage"}, {"rule": "review:missing_competency"}]) is False
    # any other cap or demotion does
    for rule in ("difficulty", "claim_conflict", "claim_pattern", "unsubstantiated", "calibration",
                 "review:contradictions", "evidence_count"):
        assert _flag(adjustments=[{"rule": rule}]) is True, rule
    assert _flag(checks=[{"issue": "off_rubric_flag", "count": 2}]) is False
    assert _flag(checks=[{"issue": "off_rubric_flag", "count": 3}]) is True
    assert _flag(checks=[{"issue": "cross_answer_risk", "count": 1}]) is True
    signals = [{"verifiable": False}] + [{"verifiable": True}] * 3
    assert _flag(answer_signals=signals) is False  # 25%
    assert _flag(answer_signals=signals + [{"verifiable": False}]) is True  # 40%
    assert _flag(claim_conflicts=[{"status": "explained"}]) is False
    for status in ("open", "asked", "unexplained"):
        assert _flag(claim_conflicts=[{"status": status}]) is True, status


def test_cross_answer_risk_never_demotes_any_verdict():
    from app.agents.reasoning.evidence_reading import evidence_reading_checks

    checks = evidence_reading_checks({"semantic_risks": ["a", "b", "c"], "per_answer": {}})
    for verdict in ("strong_hire", "hire", "lean_hire", "lean_no_hire", "no_hire"):
        final = finalize_decision({"decision": verdict, "confidence": 0.8}, checks)
        assert final["decision"] == verdict
