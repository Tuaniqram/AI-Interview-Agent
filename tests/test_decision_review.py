"""Decision review: Evidence → Draft → Self Review → Final."""
from tests.conftest import make_v4_state

from app.agents.decision.decision_review import (
    finalize_decision,
    review_decision,
)


def _state_with_evidence(
    count=6,
    avg_strength=0.7,
    contradictions=0,
    coverage=0.8,
    summary=None,
):
    evidence = [
        {
            "competency": "tech_core",
            "dimension": "technical",
            "score": 7.0,
            "strength": avg_strength,
            "contradiction": i < contradictions,
        }
        for i in range(count)
    ]
    if summary is None:
        summary = {
            "tech_core": {"evidence_count": 4, "gap": 0.1},
            "tech_db": {"evidence_count": count - 4 if count > 4 else 0, "gap": 0.2},
        }
    return make_v4_state(
        evidence_store=evidence,
        competency_summary=summary,
        hiring_recommendation={"verdict": "hire", "coverage_ratio": coverage},
    )


DRAFT_HIRE = {
    "decision": "hire",
    "confidence": 0.85,
    "rationale": "draft",
    "next_steps": [],
}


def test_review_clean_evidence_passes():
    state = _state_with_evidence(count=6, avg_strength=0.8, coverage=0.8)
    checks = review_decision(DRAFT_HIRE, state)
    assert checks == []


def test_review_flags_no_evidence_as_high():
    state = _state_with_evidence(count=0, summary={})
    checks = review_decision(DRAFT_HIRE, state)
    assert any(c["issue"] == "insufficient_evidence" and c["severity"] == "high" for c in checks)


def test_review_flags_low_evidence_as_medium():
    state = _state_with_evidence(count=2, coverage=0.8)
    checks = review_decision(DRAFT_HIRE, state)
    assert any(c["issue"] == "insufficient_evidence" and c["severity"] == "medium" for c in checks)


def test_review_flags_low_coverage_as_high():
    state = _state_with_evidence(count=6, coverage=0.3)
    checks = review_decision(DRAFT_HIRE, state)
    assert any(c["issue"] == "missing_competency" and c["severity"] == "high" for c in checks)


def test_review_flags_overconfidence_on_weak_strength():
    state = _state_with_evidence(count=6, avg_strength=0.4, coverage=0.8)
    checks = review_decision(DRAFT_HIRE, state)
    assert any(c["issue"] == "overconfidence" and c["severity"] == "medium" for c in checks)


def test_review_flags_contradictions():
    state = _state_with_evidence(count=6, contradictions=2, coverage=0.8)
    checks = review_decision(DRAFT_HIRE, state)
    assert any(c["issue"] == "contradictions" and c["severity"] == "high" for c in checks)


def test_review_orders_checks_by_severity():
    state = _state_with_evidence(count=0, summary={})
    checks = review_decision(DRAFT_HIRE, state)
    severities = [c["severity"] for c in checks]
    order = {"high": 0, "medium": 1, "low": 2}
    assert severities == sorted(severities, key=order.get)


def test_finalize_demotes_hire_on_insufficient_evidence():
    state = _state_with_evidence(count=0, summary={})
    checks = review_decision(DRAFT_HIRE, state)
    final = finalize_decision(DRAFT_HIRE, checks)
    assert final["decision"] == "insufficient_evidence"
    assert final["demoted_to_undecided"] is True
    assert final["confidence"] <= 0.5
    assert final["review"]["adjusted"] is True


def test_finalize_downgrades_confidence_without_demoting():
    state = _state_with_evidence(count=6, avg_strength=0.4, coverage=0.8)
    checks = review_decision(DRAFT_HIRE, state)
    final = finalize_decision(DRAFT_HIRE, checks)
    assert final["decision"] == "hire"
    assert final["confidence"] < 0.85
    assert final["flag_review"] is True


def test_finalize_untouched_when_clean():
    state = _state_with_evidence(count=6, avg_strength=0.8, coverage=0.8)
    checks = review_decision(DRAFT_HIRE, state)
    final = finalize_decision(DRAFT_HIRE, checks)
    assert final["decision"] == "hire"
    assert final["confidence"] == 0.85
    assert final["review"]["adjusted"] is False


def test_high_contradictions_reduce_confidence_further():
    state = _state_with_evidence(count=4, contradictions=3, coverage=0.8, avg_strength=0.5)
    checks = review_decision(DRAFT_HIRE, state)
    final = finalize_decision(DRAFT_HIRE, checks)
    assert final["confidence"] < 0.5


async def test_decision_review_node_attaches_review_trail():
    from app.agents.decision.decision_review import decision_review_node

    state = _state_with_evidence(count=0, summary={})
    state["hiring_decision"] = dict(DRAFT_HIRE)
    out = await decision_review_node(state)
    assert out["decision_review"]["checks"]
    assert out["hiring_decision"]["decision"] == "insufficient_evidence"
    assert "decision_review" in out
