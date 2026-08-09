"""Report consistency — one canonical score across recommendation, synthesis,
the persisted final_score, and the hiring decision.

Regression for the scorecard demo report that contained three competing
truths: ``strong_hire`` (composite 8.55), ``final_score`` 7.59 (a re-derived
per-turn average) and ``lean_no_hire`` (decision 4.99 anchored on a
hallucinated LLM holistic score of 4.2). The synthesis/reporting layers must
anchor every number on the same canonical composite and let the LLM narrate
only, never score.
"""
from app.agents.decision.decision_engine import decide_hiring_decision
from app.agents.decision.hiring_decision import _decision_signals
from app.agents.evaluation.synthesis import _clean_highlights, build_final_report
from app.agents.reasoning.contradiction_engine import (
    canonical_score_from_state,
    compute_canonical_score,
    evaluate_sufficiency,
)

SCORECARD_TAXONOMY = [
    {"id": "problem_solvin", "name": "Problem Solving", "category": "technical", "weight": 2.0, "default_min_evidence": 2},
    {"id": "communication", "name": "Communication", "category": "communication", "weight": 2.0, "default_min_evidence": 2},
    {"id": "system_design", "name": "System Design", "category": "technical", "weight": 1.5, "default_min_evidence": 2},
]

REQUIRED = ["problem_solvin", "communication", "system_design"]
WEIGHTS = {"problem_solvin": 2.0, "communication": 2.0, "system_design": 1.5}


def _summary(problem=8.5, comm=8.0, system=8.0, system_count=1):
    """Demo-shaped competency summary (system_design short of its minimum)."""
    return {
        "problem_solvin": {"evidence_count": 3, "average_score": problem, "gap": 0.0, "scores": [8.0, 8.5, 9.0]},
        "communication": {"evidence_count": 2, "average_score": comm, "gap": 0.0, "scores": [8.0, 8.0]},
        "system_design": {"evidence_count": system_count, "average_score": system, "gap": 0.5 if system_count < 2 else 0.0, "scores": [system]},
    }


def _hypotheses(confirmed=2, refuted=0, extra_open=9):
    hyps = []
    for i in range(confirmed):
        hyps.append({"id": f"c{i}", "competency": "problem_solvin", "direction": "positive", "status": "confirmed"})
    for i in range(refuted):
        hyps.append({"id": f"r{i}", "competency": "communication", "direction": "negative", "status": "refuted"})
    for i in range(extra_open):
        hyps.append({"id": f"o{i}", "competency": "communication", "direction": "positive", "status": "untested"})
    return hyps


def _evidence(count=6):
    return [
        {
            "id": f"ev{i}",
            "competency": ("problem_solvin" if i < 3 else "communication" if i < 5 else "system_design"),
            "score": 8.0,
            "strengths": ["Thorough response", "Real-world example", "@angular/material:cdk"],
            "weaknesses": ["Shallow analysis"],
            "question_number": i + 1,
        }
        for i in range(count)
    ]


def test_compute_canonical_score_is_the_single_composite_formula():
    """evaluate_sufficiency's composite must equal the canonical formula."""
    sufficiency, rec = evaluate_sufficiency(
        competency_summary=_summary(system_count=2),
        required_competencies=REQUIRED,
        contradictions=[],
        hypotheses=_hypotheses(),
        question_number=6,
        comp_weights=WEIGHTS,
        difficulty_reached=1,
    )
    details = sufficiency["details"]
    total_weight = sum(d["weight"] for d in details.values())
    competency_average = (
        sum(d["average_score"] * d["weight"] for d in details.values()) / total_weight
    )
    assert rec["composite_score"] == compute_canonical_score(competency_average, 1.0, 1.0)
    assert rec["composite_score"] == 9.09


def test_canonical_score_from_state_reads_recommendation():
    state = {
        "competency_summary": _summary(),
        "required_competencies": REQUIRED,
        "competency_taxonomy": SCORECARD_TAXONOMY,
        "hypotheses": _hypotheses(),
        "hiring_recommendation": {"composite_score": 8.55, "coverage_ratio": 0.73},
    }
    assert canonical_score_from_state(state) == 8.55


def test_canonical_score_from_state_recomputes_without_recommendation():
    state = {
        "competency_summary": {
            "a": {"evidence_count": 2, "average_score": 8.0, "gap": 0.0},
        },
        "required_competencies": ["a"],
        "competency_taxonomy": [{"id": "a", "weight": 2.0}],
        "hypotheses": _hypotheses(confirmed=1, extra_open=0),
    }
    assert canonical_score_from_state(state) == 9.0


def test_synthesis_holistic_anchors_canonical_never_llm():
    """An LLM claiming holistic 4.2 must NOT move the report's score."""
    state = {
        "competency_summary": _summary(),
        "evidence_store": _evidence(),
        "hypotheses": _hypotheses(),
        "difficulty_level": 1,
    }
    llm = {
        "holistic_score": 4.2,
        "narrative": "lacked experience with modern frontend frameworks",
        "fit_assessment": "Not Fit",
    }
    report = build_final_report(state, canonical=8.55, llm=llm)
    assert report["holistic_score"] == 8.55
    assert report["average_score"] == 8.55
    assert report["fit_assessment"] == "Not Fit"  # narrative fields pass through


def test_synthesis_ignores_null_legacy_fields():
    """Legacy V3 fields (skills_tested/skills_weak/coverage_map/rag_metadata)
    must be irrelevant — the report sources v5 state only."""
    state = {
        "competency_summary": _summary(),
        "evidence_store": _evidence(),
        "hypotheses": _hypotheses(),
        "difficulty_level": 1,
    }
    assert "skills_tested" not in state
    assert "rag_metadata" not in state
    report = build_final_report(state, canonical=8.55)
    assert set(report["skills_tested"]) == set(REQUIRED)
    assert report["score_timeline"] == [
        {"question": 1, "score": 8.0},
        {"question": 2, "score": 8.0},
        {"question": 3, "score": 8.0},
        {"question": 4, "score": 8.0},
        {"question": 5, "score": 8.0},
        {"question": 6, "score": 8.0},
    ]
    # strengths fall back to deduped evidence highlights when the LLM gives none
    assert "Thorough response" in report["key_strengths"]
    assert "@angular/material:cdk" not in report["key_strengths"]


def test_clean_highlights_drops_code_tokens_and_dedupes():
    cleaned = _clean_highlights([
        "@angular/material:cdk",
        "Thorough response",
        "thorough response",
        "x",
        "Deep knowledge of state management",
    ])
    assert cleaned == ["Thorough response", "Deep knowledge of state management"]


def test_summary_strengths_anchored_in_competency_evidence():
    """P4: strengths/weaknesses must be evidence-anchored — the LLM's
    delivery-style buzzwords ("Good pacing", "articulate") must not appear."""
    state = {
        "competency_summary": _summary(),
        "evidence_store": _evidence(),
        "hypotheses": _hypotheses(),
        "difficulty_level": 1,
    }
    llm = {
        "narrative": "ok",
        "fit_assessment": "Good Fit",
        "key_strengths": ["Good pacing", "Very articulate", "problem_solvin: strong evidence (3 item(s), avg 8.5/10)"],
        "key_weaknesses": ["Good engagement", "system_design: evidence gap (gap 0.50)"],
    }
    report = build_final_report(state, canonical=8.55, llm=llm)
    assert "Good pacing" not in report["key_strengths"]
    assert "Very articulate" not in report["key_strengths"]
    assert "Good engagement" not in report["key_weaknesses"]
    assert any("problem_solvin" in s for s in report["key_strengths"])
    assert any("system_design" in w for w in report["key_weaknesses"])
    # the deterministic evidence items lead the list even when the LLM is absent
    deterministic = build_final_report(state, canonical=8.55)
    assert any(s.startswith("problem_solvin") for s in deterministic["key_strengths"])
    assert any(w.startswith("system_design") for w in deterministic["key_weaknesses"])


def test_evidence_weaknesses_flag_uncovered_and_gapped_competencies():
    from app.agents.evaluation.synthesis import _evidence_weaknesses

    summary = _summary()
    summary["accessibility"] = {"evidence_count": 0, "average_score": 0.0, "gap": 1.0}
    weaknesses = _evidence_weaknesses(summary)
    assert any("accessibility: no evidence gathered" == w for w in weaknesses)
    assert any("system_design" in w and "gap" in w for w in weaknesses)


def test_hiring_decision_agrees_with_recommendation():
    """With the canonical holistic anchor, the deterministic 7-point decision
    must land on the same verdict as the evidence-grounded recommendation —
    provided the coverage cap (>=85% for strong_hire) is met."""
    state = {
        "competency_summary": _summary(),
        "evidence_store": _evidence(),
        "hypotheses": _hypotheses(),
        "contradictions": [],
        "difficulty_level": 5,
        "final_report": {"holistic_score": 8.55},
        "hiring_recommendation": {
            "verdict": "strong_hire",
            "composite_score": 8.55,
            "coverage_ratio": 0.9,
        },
    }
    decision = decide_hiring_decision(**_decision_signals(state))
    assert decision["decision"] == "strong_hire"
    assert decision["decision"] == state["hiring_recommendation"]["verdict"]
    assert decision["decision_score"] >= 8.5


def test_hiring_decision_not_strong_hire_at_difficulty_one():
    """D2: the same evidence profile at difficulty 1 must NOT yield a
    strong_hire — the engine discounts un-stress-tested evidence."""
    state = {
        "competency_summary": _summary(),
        "evidence_store": _evidence(),
        "hypotheses": _hypotheses(),
        "contradictions": [],
        "difficulty_level": 1,
        "final_report": {"holistic_score": 8.55},
        "hiring_recommendation": {
            "verdict": "strong_hire",
            "composite_score": 8.55,
            "coverage_ratio": 0.73,
        },
    }
    decision = decide_hiring_decision(**_decision_signals(state))
    assert decision["decision"] != "strong_hire"
    assert decision["decision_score"] < 8.5


async def test_hiring_decision_llm_explains_never_decides(stub_llm):
    """The LLM must explain the engine's decision, never replace it: a
    contradictory LLM verdict must not leak into the report."""
    import json

    from app.agents.decision.hiring_decision import hiring_decision_node

    state = {
        "job_role": "Senior Frontend",
        "competency_summary": _summary(),
        "evidence_store": _evidence(),
        "hypotheses": _hypotheses(),
        "contradictions": [],
        "difficulty_level": 5,
        "final_report": {"holistic_score": 8.55},
        "hiring_recommendation": {
            "verdict": "strong_hire",
            "composite_score": 8.55,
            "coverage_ratio": 0.9,
        },
    }
    stub_llm(response=json.dumps({
        "decision": "no_hire",
        "confidence": 0.1,
        "rationale": "weaknesses prevent a strong_hire recommendation",
        "next_steps": ["reject"],
    }))
    out = await hiring_decision_node(state)
    hd = out["hiring_decision"]
    assert hd["decision"] == "strong_hire"  # the engine wins
    assert "decision" not in hd["llm_draft"]  # the LLM never offers one
    assert "confidence" not in hd["llm_draft"]
    assert hd["confidence"] > 0.5  # deterministic confidence, not the LLM's 0.1
    assert "weaknesses prevent" not in hd["rationale"]


async def test_decision_confidence_tempered_by_weaknesses(stub_llm):
    """D4: a report full of flagged weaknesses must not carry near-max
    confidence — the deterministic confidence shaves for weaknesses,
    falsified hypotheses and contradictions."""
    import json

    from app.agents.decision.hiring_decision import hiring_decision_node

    def run_with(weaknesses):
        state = {
            "job_role": "Senior Frontend",
            "competency_summary": _summary(),
            "evidence_store": _evidence(),
            "hypotheses": _hypotheses(),
            "contradictions": [],
            "difficulty_level": 5,
            "final_report": {
                "holistic_score": 8.55,
                "key_weaknesses": weaknesses,
            },
            "hiring_recommendation": {
                "verdict": "strong_hire",
                "composite_score": 8.55,
                "coverage_ratio": 0.73,
            },
        }
        return state

    stub_llm(response=json.dumps({"rationale": "r", "next_steps": []}))
    clean = await hiring_decision_node(run_with([]))
    flagged = await hiring_decision_node(run_with([
        "system_design: weak performance",
        "accessibility: no evidence gathered",
        "testing: evidence gap",
    ]))
    clean = await hiring_decision_node(run_with([]))
    flagged = await hiring_decision_node(run_with([
        "system_design: weak performance",
        "accessibility: no evidence gathered",
        "testing: evidence gap",
    ]))
    assert clean["hiring_decision"]["confidence"] > flagged["hiring_decision"]["confidence"]
    assert flagged["hiring_decision"]["confidence"] < 0.8


def test_recommendation_capped_at_difficulty_one():
    """V5: the recommendation must never say hire/strong_hire from a session
    that never left difficulty 1 — same philosophy as the decision credit, so
    the two layers stop disagreeing (demo: strong_hire vs lean_hire)."""
    sufficiency, rec = evaluate_sufficiency(
        competency_summary=_summary(system_count=2),
        required_competencies=REQUIRED,
        contradictions=[],
        hypotheses=_hypotheses(),
        question_number=6,
        comp_weights=WEIGHTS,
        difficulty_reached=1,
    )
    assert rec["verdict"] == "borderline"
    assert rec["composite_score"] == 9.09  # composite stays canonical


def test_recommendation_uncapped_at_top_difficulty():
    sufficiency, rec = evaluate_sufficiency(
        competency_summary=_summary(system_count=2),
        required_competencies=REQUIRED,
        contradictions=[],
        hypotheses=_hypotheses(),
        question_number=6,
        comp_weights=WEIGHTS,
        difficulty_reached=5,
    )
    assert rec["verdict"] == "strong_hire"


def test_report_verdict_is_single_source_deterministic():
    """V5: build_report_response must surface ONE verdict — the deterministic
    decision — even when the raw recommendation disagrees."""
    from app.engine.builders import build_report_response

    state = {
        "status": "completed",
        "hiring_recommendation": {
            "verdict": "strong_hire",
            "confidence": 0.6,
            "composite_score": 9.0,
            "coverage_ratio": 1.0,
        },
        "hiring_decision": {
            "decision": "lean_hire",
            "decision_score": 7.09,
            "decision_scale": "7_point",
            "confidence": 0.5,
        },
        "competency_summary": _summary(),
        "difficulty_level": 1,
        "hypotheses": _hypotheses(),
        "evidence_store": _evidence(),
        "question_number": 5,
        "total_questions": 0,
    }
    report = build_report_response(state)
    assert report["verdict"] == "lean_hire"
    assert report["hiring_recommendation"]["verdict"] == "lean_hire"
    assert report["hiring_recommendation"]["decision_score"] == 7.09
    assert report["hiring_decision"]["decision"] == "lean_hire"
