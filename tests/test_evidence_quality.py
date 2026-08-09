"""Evidence quality signals: strength, impact, ownership, complexity,
contradiction linkage, and the confidence-weighted competency summary."""
from tests.conftest import make_v4_state

from app.agents.reasoning.evidence_engine import (
    MAX_CLAIMS_PER_ANSWER,
    annotate_evidence_quality,
    build_candidate_evidence,
    build_dimension_metrics,
    build_evidence_records,
    complexity_signal,
    compute_evidence_impact,
    compute_evidence_strength,
    detect_evidence_contradiction,
    evidence_extractor_node,
    ownership_signal,
    update_competency_summary,
)


def test_strength_is_score_tempered_by_confidence():
    assert compute_evidence_strength(8.0, 0.9) == 0.72
    assert compute_evidence_strength(10.0, 1.0) == 1.0
    assert compute_evidence_strength(8.0, 0.5) == 0.4
    assert 0.0 <= compute_evidence_strength(-3, 2.0) <= 1.0


def test_impact_maximizes_off_midpoint_with_high_confidence():
    assert compute_evidence_impact(10.0, 1.0) == 1.0
    assert compute_evidence_impact(5.0, 1.0) == 0.0
    assert compute_evidence_impact(9.0, 0.5) == 0.4
    assert 0.0 <= compute_evidence_impact(0.0, 0.0) <= 1.0


def test_ownership_signal_labels_attribution():
    assert ownership_signal("I built the queue service end to end") == "first_person"
    assert ownership_signal("We shipped the migration together") == "team"
    assert ownership_signal("The team was asked to redesign it") == "third_person"
    assert ownership_signal("") == "vague"


def test_complexity_signal_buckets_specificity():
    rich = (
        "I architected a distributed pipeline with a queue and cache, reducing "
        "latency from 1200ms to 200ms for 3 million requests a day across the "
        "kubernetes cluster.\n```python\ndef retry(handler): ...\n```"
    )
    assert complexity_signal(rich) == "high"
    assert complexity_signal("I did some work") == "low"
    assert complexity_signal("") == "low"


def test_build_evidence_records_annotates_quality():
    records = build_evidence_records(
        evaluation={
            "technical": {"score": 9.0, "confidence": 0.8, "evidence": "I built it", "strengths": [], "weaknesses": []},
        },
        question="Tell me about X",
        question_number=1,
        session_id="s1",
        question_objective={"target_competency": "tech_core"},
    )
    assert len(records) == 1
    rec = records[0]
    assert rec["strength"] == 0.72
    assert rec["impact"] == 0.64
    assert rec["ownership"] == "first_person"
    assert rec["complexity"] in {"high", "medium", "low"}
    assert rec["contradiction"] is False


def test_contradiction_detected_against_prior_average():
    record = {"competency": "tech_core", "score": 9.0}
    no_history = {"tech_core": {"evidence_count": 0, "average_score": 0.0}}
    assert detect_evidence_contradiction(record, no_history) is False
    conflicting = {"tech_core": {"evidence_count": 3, "average_score": 3.0}}
    assert detect_evidence_contradiction(record, conflicting) is True
    aligned = {"tech_core": {"evidence_count": 3, "average_score": 8.0}}
    assert detect_evidence_contradiction(record, aligned) is False


def test_annotate_evidence_quality_overrides_contradiction():
    record = {
        "competency": "tech_core",
        "score": 9.0,
        "confidence": 0.8,
        "evidence_text": "I built the whole thing myself",
    }
    annotate_evidence_quality(record, {"tech_core": {"evidence_count": 2, "average_score": 2.0}})
    assert record["contradiction"] is True
    assert record["strength"] == 0.72


def test_summary_tracks_average_strength():
    records = [
        {"competency": "tech_core", "score": 8.0, "confidence": 0.9, "strength": 0.72, "evidence_text": "x"},
        {"competency": "tech_core", "score": 6.0, "confidence": 0.5, "strength": 0.3, "evidence_text": "y"},
    ]
    summary = update_competency_summary({}, records)
    comp = summary["tech_core"]
    assert comp["evidence_count"] == 2
    assert comp["average_score"] == 7.0
    assert comp["average_strength"] == 0.51
    assert comp["average_confidence"] == 0.7


def test_summary_gap_recomputes_from_min_evidence():
    record = {"competency": "tech_core", "score": 8.0, "confidence": 0.9, "evidence_text": "x"}
    summary = update_competency_summary(
        {}, [record], min_evidence_map={"tech_core": 2}
    )
    assert summary["tech_core"]["gap"] == 0.5
    assert summary["tech_core"]["coverage"] == 0.5
    summary2 = update_competency_summary(
        summary,
        [{"competency": "tech_core", "score": 7.0, "confidence": 0.8, "evidence_text": "y"}],
        min_evidence_map={"tech_core": 2},
    )
    assert summary2["tech_core"]["gap"] == 0.0
    assert summary2["tech_core"]["coverage"] == 1.0


def test_summary_defaults_min_evidence_to_two():
    records = [
        {"competency": "tech_core", "score": 8.0, "confidence": 0.9, "evidence_text": "x"},
        {"competency": "tech_core", "score": 7.0, "confidence": 0.8, "evidence_text": "y"},
    ]
    summary = update_competency_summary({}, records)
    assert summary["tech_core"]["gap"] == 0.0


async def test_extractor_node_flags_contradiction_vs_existing_evidence():
    prior_summary = {
        "tech_core": {"evidence_count": 2, "average_score": 2.0, "scores": [2.0, 2.0], "average_strength": 0.18},
    }
    state = await evidence_extractor_node(make_v4_state(
        question_number=3,
        current_question="Q3",
        question_objective={"target_competency": "tech_core"},
        competency_summary=prior_summary,
        unified_evaluation={
            "technical": {"score": 9.0, "confidence": 0.9, "evidence": "I scaled the database cluster", "strengths": [], "weaknesses": []},
        },
    ))
    rec = state["extracted_evidence"][0]
    assert rec["contradiction"] is True
    assert state["competency_summary"]["tech_core"]["evidence_count"] == 3
    assert state["competency_summary"]["tech_core"]["average_strength"] == 0.39


async def test_extractor_node_leaves_consistent_evidence_unaligned():
    prior_summary = {"tech_core": {"evidence_count": 2, "average_score": 8.5, "scores": [8.0, 9.0]}}
    state = await evidence_extractor_node(make_v4_state(
        question_number=3,
        current_question="Q3",
        question_objective={"target_competency": "tech_core"},
        competency_summary=prior_summary,
        unified_evaluation={
            "technical": {"score": 9.0, "confidence": 0.9, "evidence": "Strong", "strengths": [], "weaknesses": []},
        },
    ))
    assert state["extracted_evidence"][0]["contradiction"] is False


def test_candidate_evidence_only_uses_top_scoring_dimension():
    records = build_candidate_evidence(
        evaluation={
            "technical": {"score": 8.0, "confidence": 0.9, "evidence": "Solid technical depth here.", "strengths": [], "weaknesses": []},
            "behavioral": {"score": 6.0, "confidence": 0.7, "evidence": "Decent teamwork.", "strengths": [], "weaknesses": []},
            "completeness": {"score": 7.0, "confidence": 0.8, "evidence": "Complete answer.", "strengths": [], "weaknesses": []},
        },
        question="Q",
        question_number=1,
        session_id="s1",
        question_objective={"target_competency": "tech_core"},
    )
    assert records
    assert all(r["dimension"] == "technical" for r in records)
    assert len(records) <= MAX_CLAIMS_PER_ANSWER


def test_candidate_evidence_normalizes_competency_alias():
    records = build_candidate_evidence(
        evaluation={
            "technical": {"score": 9.0, "confidence": 0.8, "evidence": "I built it", "strengths": [], "weaknesses": []},
        },
        question="Tell me about X",
        question_number=1,
        session_id="s1",
        question_objective={"target_competency": "project management"},
    )
    assert records
    assert all(r["competency"] == "exp_project_depth" for r in records)


def test_candidate_evidence_no_inflation_on_multi_dimension_evaluation():
    records = build_candidate_evidence(
        evaluation={
            "technical": {"score": 8.0, "confidence": 0.9, "evidence": "I built a distributed pipeline.", "strengths": [], "weaknesses": []},
            "communication": {"score": 8.0, "confidence": 0.9, "evidence": "Clear talk.", "strengths": [], "weaknesses": []},
        },
        question="Q",
        question_number=1,
        session_id="s1",
        question_objective={"target_competency": "tech_core"},
    )
    assert len(records) == 1
    assert records[0]["score"] == 8.0


def test_candidate_evidence_keeps_reading_order_for_two_claims():
    text = "I built the queue service. I scaled it to handle three million requests per day across the kubernetes cluster."
    records = build_candidate_evidence(
        evaluation={"technical": {"score": 9.0, "confidence": 0.9, "evidence": text, "strengths": [], "weaknesses": []}},
        question="Q",
        question_number=2,
        session_id="s1",
        question_objective={"target_competency": "tech_core"},
    )
    assert len(records) == 2
    assert records[0]["evidence_text"] == "I built the queue service."
    assert records[1]["evidence_text"].startswith("I scaled it")


def test_candidate_evidence_empty_text_yields_no_claims():
    records = build_candidate_evidence(
        evaluation={"technical": {"score": 8.0, "confidence": 0.9, "evidence": "", "strengths": [], "weaknesses": []}},
        question="Q",
        question_number=3,
        session_id="s1",
        question_objective={"target_competency": "tech_core"},
    )
    assert records == []


def test_candidate_evidence_ties_break_to_technical_priority():
    records = build_candidate_evidence(
        evaluation={
            "behavioral": {"score": 8.0, "confidence": 0.9, "evidence": "Good teamwork story here.", "strengths": [], "weaknesses": []},
            "technical": {"score": 8.0, "confidence": 0.9, "evidence": "Great system design.", "strengths": [], "weaknesses": []},
        },
        question="Q",
        question_number=4,
        session_id="s1",
        question_objective={"target_competency": "tech_core"},
    )
    assert records and records[0]["dimension"] == "technical"


def test_build_dimension_metrics_records_all_scored_dimensions():
    metrics = build_dimension_metrics(
        {
            "technical": {"score": 8.0, "confidence": 0.9, "evidence": "x"},
            "behavioral": {"score": None, "confidence": 0.0, "evidence": "n/a"},
        },
        top_dimension="technical",
        claims_extracted=1,
    )
    assert metrics["top_dimension"] == "technical"
    assert metrics["claims_extracted"] == 1
    assert set(metrics["dimensions"]) == {"technical"}
    assert metrics["dimensions"]["technical"]["has_evidence"] is True


async def test_extractor_node_tracks_dimension_metrics_history(fake_evidence_repo):
    evaluation = {
        "technical": {"score": 8.0, "confidence": 0.9, "evidence": "Solid answer.", "strengths": [], "weaknesses": []},
        "behavioral": {"score": 6.0, "confidence": 0.7, "evidence": "Okay story.", "strengths": [], "weaknesses": []},
    }
    state = await evidence_extractor_node(make_v4_state(
        question_number=1,
        current_question="Q1",
        question_objective={"target_competency": "tech_core"},
        unified_evaluation=evaluation,
    ))
    assert len(state["dimension_metrics"]) == 1
    entry = state["dimension_metrics"][0]
    assert entry["top_dimension"] == "technical"
    assert set(entry["dimensions"]) == {"technical", "behavioral"}
    assert len(state["extracted_evidence"]) == 1


async def test_extractor_node_zero_claims_still_records_metrics(fake_evidence_repo):
    state = await evidence_extractor_node(make_v4_state(
        question_number=2,
        current_question="Q2",
        question_objective={"target_competency": "tech_core"},
        unified_evaluation={
            "technical": {"score": 8.0, "confidence": 0.9, "evidence": "", "strengths": [], "weaknesses": []},
        },
    ))
    assert state["dimension_metrics"][-1]["claims_extracted"] == 0
    assert state["extracted_evidence"] == []


def test_candidate_evidence_maps_dimension_to_taxonomy_competency():
    """Fix 11: without a question objective, records land on the taxonomy
    competency that lists the top dimension — never on bare dim_* nodes."""
    records = build_candidate_evidence(
        evaluation={
            "communication": {"score": 9.0, "confidence": 0.9, "evidence": "Clear stakeholder updates.", "strengths": [], "weaknesses": []},
        },
        question="Q",
        question_number=1,
        session_id="s1",
    )
    assert records
    assert records[0]["competency"] == "behav_communication"
    assert not records[0]["competency"].startswith("dim_")


def test_candidate_evidence_falls_back_for_unmappable_dimension():
    """When the taxonomy cannot map the top dimension (empty/unknown set), no
    ``dim_*`` record is fabricated — the evidence falls back to the taxonomy's
    first competency (tech_core) so the answer is never dropped."""
    records = build_candidate_evidence(
        evaluation={
            "confidence": {"score": 9.0, "confidence": 0.9, "evidence": "Very sure of myself here.", "strengths": [], "weaknesses": []},
        },
        question="Q",
        question_number=1,
        session_id="s1",
        competency_taxonomy=[],
    )
    assert len(records) == 1
    assert records[0]["competency"] == "tech_core"
    assert not records[0]["competency"].startswith("dim_")
