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
    transcript_payload,
)
from app.brain.evidence_reasoner import classify_claim, evidence_summary_stats
from app.agents.decision.decision_review import finalize_decision, review_decision
from tests.conftest import make_v4_state

EVIDENCE_READING_JSON = json.dumps({
    "per_answer": [
        {
            "evidence_id": "e1",
            "claim_classification": "proven",
            "verifiable": True,
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
                        "verifiable": "yes", "specificity": "max", "ownership": "god"}],
    })
    entry = out["per_answer"]["e1"]
    assert entry["claim_classification"] == "mentioned"
    assert entry["verifiable"] is True  # truthy string coerced to bool
    assert entry["specificity"] == "low"
    assert entry["ownership"] == "vague"


def test_risk_flags_and_checks_capped_at_medium():
    reading = {
        "off_rubric": {"red_flags": ["overstated ownership"], "hidden_strengths": []},
        "semantic_risks": ["Q3 vs Q8 mismatch"],
        "per_answer": {f"e{i}": {"verifiable": False} for i in range(4)},
    }
    flags = evidence_reading_risk_flags(reading)
    assert any("off-rubric flag" in f for f in flags)
    assert any("cross-answer risk" in f for f in flags)
    assert any("not backed by specifics" in f for f in flags)

    checks = evidence_reading_checks(reading)
    assert checks
    assert all(c["severity"] == "medium" for c in checks), checks
    assert not any(c["severity"] == "high" for c in checks)


def test_transcript_payload_is_capped_and_deterministic():
    store = [{"id": f"e{i}", "evidence_text": "x" * 5000} for i in range(30)]
    payload = transcript_payload(store)
    assert len(payload) == 20
    assert all(len(item["evidence_text"]) <= 2000 for item in payload)


async def test_evidence_reading_node_populates_state(stub_llm):
    stub = stub_llm(response=EVIDENCE_READING_JSON)
    from app.agents.evaluation.evidence_reading import evidence_reading_node

    state = make_v4_state(
        job_role="Backend Engineer",
        evidence_store=[{"id": "e1", "evidence_text": "I owned the event pipeline."}],
    )
    out = await evidence_reading_node(state)
    assert out["evidence_reading"]["per_answer"]["e1"]["claim_classification"] == "proven"
    assert stub.calls[0]["tier"] == "strong"
    assert "Evidence Reading" in stub.calls[0]["prompt"]


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
        evidence_store=[
            {"strength": 0.8} for _ in range(4)
        ],
        evidence_reading={
            "off_rubric": {"red_flags": ["overstated ownership"], "hidden_strengths": []},
            "semantic_risks": ["Q3 vs Q8 mismatch"],
            "per_answer": {},
        },
    )
    draft = state["hiring_decision"]
    checks = review_decision(draft, state)
    assert any(c["issue"] in ("off_rubric_flag", "cross_answer_risk") for c in checks)

    final = finalize_decision(draft, checks)
    # Medium-only semantic checks: flag for review + trim confidence, never demote.
    assert final["decision"] == "hire"
    assert final["flag_review"] is True
    assert final["confidence"] < 0.7


def test_decision_review_without_reading_is_unchanged():
    state = make_v4_state(
        hiring_decision={"decision": "hire", "decision_score": 8.0, "confidence": 0.7},
        hiring_recommendation={"verdict": "hire", "coverage_ratio": 0.9},
        evidence_store=[{"strength": 0.8} for _ in range(4)],
    )
    draft = state["hiring_decision"]
    checks = review_decision(draft, state)
    assert not any(c["issue"] in ("off_rubric_flag", "cross_answer_risk", "unverifiable_claims") for c in checks)
    final = finalize_decision(draft, checks)
    assert final["decision"] == "hire"
    assert final.get("flag_review", False) is False
    assert final["confidence"] == 0.7
