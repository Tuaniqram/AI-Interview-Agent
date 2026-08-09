"""AURA Brain V5 — multi-layer brain assembler tests.

Covers the user-facing acceptance criteria:
    * two DIFFERENT roles produce two DIFFERENT brains (mission, critical
      competencies, competency graph, question strategy)
    * competencies are a GRAPH (parent -> specialized children)
    * hypotheses carry confidence + collected + MISSING evidence
    * evidence graph uses typed edges (supports/contradicts/required_for)
      with claim confidence (mentioned/demonstrated/proven)
    * the planner reduces uncertainty (mode + planned competency)
    * calibration never trusts bare score > 8 with thin evidence
    * decision state carries risk flags
"""
import pytest

from app.brain import assemble_aura_brain
from app.brain.assembler import build_aura_from_state, refresh_brain_layers
from app.brain.calibration import (
    calibrated_quality,
    evidence_depth,
)
from app.brain.company_brain import build_v5_company_brain, infer_engineering_philosophy
from app.brain.contradiction_detector import build_contradiction_state, seniority_claim_risk
from app.brain.evidence_reasoner import classify_claim, evidence_summary_stats, evidence_to_graph
from app.brain.hypothesis_engine import (
    build_hypothesis_brain,
    missing_evidence_for,
    uncertainty_map,
)
from app.brain.question_planner import generate_question_strategy
from app.brain.role_brain import build_role_brain, classify_seniority, detect_role_class
from app.data.competency_graph import competency_children, taxonomy_to_graph
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY

BACKEND_TAXONOMY = [
    {"id": "tech_system_design", "name": "System Design & Architecture", "category": "technical", "weight": 3.0},
    {"id": "tech_event_driven", "name": "Event-Driven Systems", "category": "technical", "weight": 2.0},
    {"id": "tech_core", "name": "Core Language Proficiency", "category": "technical", "weight": 2.0},
    {"id": "behav_communication", "name": "Communication Clarity", "category": "behavioral", "weight": 1.0},
]
FRONTEND_TAXONOMY = [
    {"id": "tech_framework", "name": "Framework & Library Knowledge", "category": "technical", "weight": 3.0},
    {"id": "tech_core", "name": "Core Language Proficiency", "category": "technical", "weight": 2.0},
    {"id": "behav_communication", "name": "Communication Clarity", "category": "behavioral", "weight": 2.0},
    {"id": "cog_problem_solving", "name": "Problem Solving", "category": "cognitive", "weight": 2.0},
]

HYPOTHESES = [
    {"id": "h1", "competency": "tech_system_design", "statement": "Candidate designs scalable systems", "confidence": 0.45, "probability": 0.45, "status": "testing", "required_evidence": 3, "direction": "positive"},
    {"id": "h2", "competency": "tech_event_driven", "statement": "Candidate builds event-driven flows", "confidence": 0.6, "probability": 0.6, "status": "untested", "required_evidence": 3, "direction": "positive"},
]

STRONG_EVIDENCE = [
    {"id": "e1", "competency": "tech_system_design", "score": 8.2, "confidence": 0.8, "ownership": "first_person", "complexity": "high",
     "evidence_text": "I architected a microservices platform and owned the Kafka event pipeline; we reduced p99 latency 40%", "question_number": 1},
    {"id": "e2", "competency": "tech_system_design", "score": 7.8, "confidence": 0.7, "ownership": "first_person", "complexity": "high",
     "evidence_text": "I designed the database schema, sharded it, and explained the tradeoff with the team", "question_number": 2},
]

WEAK_SENIORITY_CLAIMS = [
    {"id": "w1", "competency": "tech_system_design", "score": 8.0, "confidence": 0.6,
     "evidence_text": "I used Kafka in the architecture", "question_number": 1},
    {"id": "w2", "competency": "tech_system_design", "score": 8.5, "confidence": 0.6,
     "evidence_text": "We had microservices with event-driven design", "question_number": 2},
]


def _base_kwargs(**overrides):
    kwargs = {
        "job_role": "Senior Backend Engineer",
        "company_brain": {"tech_stack": ["Kubernetes", "Kafka", "PostgreSQL"], "culture": ["ownership", "experimentation"], "process": ["code review", "CI/CD"]},
        "taxonomy": BACKEND_TAXONOMY,
        "required_competencies": ["tech_system_design", "tech_event_driven"],
        "hypotheses": HYPOTHESES,
        "evidence_store": STRONG_EVIDENCE,
        "competency_summary": {"tech_system_design": {"evidence_count": 2, "gap": 0.0, "average_score": 8.0}},
        "difficulty_reached": 3,
        "role_floor": 3,
        "hiring_recommendation": {"verdict": "hire", "composite_score": 8.2, "confidence_v2": 0.7, "confidence": 0.7},
        "hiring_decision": {"decision": "hire", "decision_score": 8.2, "confidence": 0.7},
    }
    kwargs.update(overrides)
    return kwargs


# --------------------------------------------------------------------------- #
# Layer 1: company brain                                                      #
# --------------------------------------------------------------------------- #


def test_company_brain_carries_engineering_dna():
    v5 = build_v5_company_brain(
        {"tech_stack": ["Kubernetes", "Kafka"], "culture": ["ownership", "experimentation"], "summary": "cloud-native with automated testing"},
        job_role="Senior Backend Engineer",
    )
    assert v5["engineering_philosophy"]["architecture_style"] == "distributed_services"
    assert v5["engineering_philosophy"]["ownership_model"] == "strong_ownership"
    assert "ownership" in v5["culture_signals"]
    assert "avoid" in v5["failure_patterns"]
    assert v5["technical_expectations"]["senior"]["expected_behavior"]
    assert "design independently" in v5["senior_expectations"]


def test_engineering_philosophy_keyword_detection():
    assert infer_engineering_philosophy({"culture": ["experimentation"], "process": ["weekly releases"]})["speed_vs_quality"] == "speed_first"
    assert infer_engineering_philosophy({})["architecture_style"] == "monolith"


# --------------------------------------------------------------------------- #
# Layer 2: role brain (knowledge base, not random LLM)                        #
# --------------------------------------------------------------------------- #


def test_role_classes_and_seniority():
    assert detect_role_class("Senior Backend Engineer")[0] == "backend"
    assert detect_role_class("Senior Frontend Engineer")[0] == "frontend"
    assert detect_role_class("Machine Learning Engineer")[0] == "ml"
    assert classify_seniority("Staff Frontend Engineer") == "staff"
    assert classify_seniority("Junior Developer") == "junior"


def test_role_brains_differ_between_roles():
    backend = build_role_brain(job_role="Senior Backend Engineer", taxonomy=BACKEND_TAXONOMY, required_competencies=["tech_system_design", "tech_event_driven"])
    frontend = build_role_brain(job_role="Senior Frontend Engineer", taxonomy=FRONTEND_TAXONOMY, required_competencies=["tech_framework"])

    assert backend["mission"] != frontend["mission"]
    assert backend["class"] == "backend" and frontend["class"] == "frontend"
    assert [c["id"] for c in backend["critical_competencies"]] != [c["id"] for c in frontend["critical_competencies"]]

    system_design = next(c for c in backend["critical_competencies"] if c["id"] == "tech_system_design")
    assert system_design["importance"] == 10
    assert system_design["must_prove"]

    framework = next(c for c in frontend["critical_competencies"] if c["id"] == "tech_framework")
    assert framework["importance"] >= 8


# --------------------------------------------------------------------------- #
# Layer 3: competency graph                                                   #
# --------------------------------------------------------------------------- #


def test_competency_graph_is_a_graph_not_a_list():
    assert "scalability" in competency_children("tech_system_design")
    assert "kafka" in competency_children("tech_event_driven")
    assert competency_children("tech_system_design")


def test_session_graph_projects_required_only():
    graph = taxonomy_to_graph(BACKEND_TAXONOMY, ["tech_system_design"])
    nodes = graph["nodes"]
    assert nodes["tech_system_design"]["scope"] == "required"
    assert nodes["tech_event_driven"]["scope"] == "context"
    assert any(e["relation"] == "specializes" for e in graph["edges"])


# --------------------------------------------------------------------------- #
# Layer 4: hypothesis engine (missing evidence)                               #
# --------------------------------------------------------------------------- #


def test_hypothesis_missing_evidence_tracked():
    hyp = {"id": "h1", "competency": "tech_system_design", "required_evidence": 3}
    missing = missing_evidence_for(hyp, STRONG_EVIDENCE, taxonomy_to_graph(BACKEND_TAXONOMY, None))
    assert isinstance(missing, list)
    assert "architecture_decision" in missing


def test_hypothesis_brain_uncertainty():
    brain = build_hypothesis_brain(HYPOTHESES, STRONG_EVIDENCE, {"tech_system_design": {"evidence_count": 2}}, role_brain=None)
    h1 = next(h for h in brain if h["id"] == "h1")
    assert "missing_evidence" in h1
    assert 0.0 < h1["uncertainty"] <= 1.0
    h2 = next(h for h in brain if h["id"] == "h2")
    assert h2["status"] == "untested"
    assert h2["uncertainty"] > h1["uncertainty"]


# --------------------------------------------------------------------------- #
# Layer 5: evidence graph (typed edges)                                       #
# --------------------------------------------------------------------------- #


def test_claim_classification():
    assert classify_claim({"ownership": "first_person", "complexity": "high"}) == "proven"
    assert classify_claim({"ownership": "first_person", "complexity": "medium"}) == "demonstrated"
    assert classify_claim({"ownership": "third_person", "complexity": "low"}) == "mentioned"


def test_typed_evidence_graph_edges():
    graph = evidence_to_graph(STRONG_EVIDENCE, competency_graph=taxonomy_to_graph(BACKEND_TAXONOMY, None), role_brain={"role": "Senior Backend Engineer", "class": "backend"})
    relations = {e["relation"] for e in graph["edges"]}
    assert "supports" in relations
    assert "required_for" in relations
    assert all(e.get("confidence", 1.0) > 0 for e in graph["edges"])
    stats = evidence_summary_stats(STRONG_EVIDENCE)
    assert stats["proven"] >= 2
    assert stats["proof_ratio"] > 0.5


# --------------------------------------------------------------------------- #
# Layer 6: contradiction / fake-seniority                                     #
# --------------------------------------------------------------------------- #


def test_seniority_risk_flags_thin_claims():
    risk = seniority_claim_risk(WEAK_SENIORITY_CLAIMS, None, None)
    assert risk["level"] in ("high", "medium")
    assert risk["action"] == "challenge"
    assert risk["probe_questions"]


def test_seniority_risk_low_when_proven():
    risk = seniority_claim_risk(STRONG_EVIDENCE, None, None)
    assert risk["level"] == "low"


# --------------------------------------------------------------------------- #
# Layer 7: question planner (reduce uncertainty)                              #
# --------------------------------------------------------------------------- #


def test_planner_targets_highest_uncertainty():
    hyp_brain = build_hypothesis_brain(HYPOTHESES, STRONG_EVIDENCE, {"tech_system_design": {"evidence_count": 2}})
    umap = uncertainty_map(hyp_brain, {"tech_system_design": {"evidence_count": 2, "gap": 0.0}}, BACKEND_TAXONOMY)
    strategy = generate_question_strategy(
        uncertainty_map=umap,
        contradiction_state={"needs_challenge": False, "contradictions": [], "seniority_risk": {"level": "low", "action": "validate"}},
        hypothesis_brain=hyp_brain,
    )
    assert strategy["planned_competency"] == "tech_event_driven"
    assert strategy["question_strategy"]["mode"] == "explore"


def test_planner_challenges_claimed_seniority():
    strategy = generate_question_strategy(
        uncertainty_map={"tech_system_design": {"competency": "tech_system_design", "uncertainty": 0.5, "importance": 10, "missing_evidence": ["tradeoffs"]}},
        contradiction_state={"needs_challenge": True, "contradictions": [], "seniority_risk": {"level": "high", "action": "challenge"}},
        hypothesis_brain=[],
    )
    assert strategy["question_strategy"]["mode"] == "challenge"


# --------------------------------------------------------------------------- #
# Layer 8: calibration                                                         #
# --------------------------------------------------------------------------- #


def test_calibration_caps_high_score_on_thin_evidence():
    score = calibrated_quality(
        composite_score=9.0, total_evidence=2, difficulty_reached=1, role_floor=3,
        proof_ratio=0.5, resolved_ratio=0.0, serious_contradictions=0,
    )
    assert score <= 7.0
    assert evidence_depth(2) == "low"


def test_calibration_rewards_proven_depth():
    deep = calibrated_quality(
        composite_score=8.0, total_evidence=15, difficulty_reached=4, role_floor=3,
        proof_ratio=0.9, resolved_ratio=0.8, serious_contradictions=0,
    )
    assert deep > 7.0


# --------------------------------------------------------------------------- #
# Assembler acceptance                                                        #
# --------------------------------------------------------------------------- #


def test_assemble_aura_brain_full_shape():
    brain = assemble_aura_brain(**_base_kwargs())
    for section in (
        "company_brain", "role_brain", "competency_graph", "hypotheses",
        "evidence_graph", "uncertainty_map", "question_strategy",
        "difficulty_state", "contradiction_state", "calibration_state",
        "decision_state",
    ):
        assert section in brain, section
    assert brain["difficulty_state"]["floor_satisfied"] is True
    assert brain["calibration_state"]["evidence_depth"] == "low"
    assert brain["decision_state"]["decision"] == "hire"


def test_two_roles_two_different_brains():
    backend = assemble_aura_brain(**_base_kwargs())
    frontend = assemble_aura_brain(
        job_role="Senior Frontend Engineer",
        company_brain={"tech_stack": ["React", "TypeScript"]},
        taxonomy=FRONTEND_TAXONOMY,
        required_competencies=["tech_framework"],
        hypotheses=[{"id": "h3", "competency": "tech_framework", "statement": "Candidate masters the framework", "confidence": 0.5, "status": "untested", "required_evidence": 3, "direction": "positive"}],
        evidence_store=[],
        competency_summary={},
        difficulty_reached=1,
        role_floor=3,
    )
    assert backend["role_brain"]["class"] != frontend["role_brain"]["class"]
    assert backend["role_brain"]["mission"] != frontend["role_brain"]["mission"]
    assert [c["id"] for c in backend["role_brain"]["critical_competencies"]] != [c["id"] for c in frontend["role_brain"]["critical_competencies"]]
    assert set(backend["competency_graph"]["nodes"]) != set(frontend["competency_graph"]["nodes"])


def test_build_aura_from_state_engine_path():
    state = {
        "job_role": "Senior Backend Engineer",
        "company_brain": {"tech_stack": ["Kafka"]},
        "competency_taxonomy": BACKEND_TAXONOMY,
        "required_competencies": ["tech_system_design"],
        "hypotheses": HYPOTHESES,
        "evidence_store": STRONG_EVIDENCE,
        "competency_summary": {"tech_system_design": {"evidence_count": 2, "gap": 0.0}},
        "contradictions": [],
        "difficulty_level": 3,
        "hiring_recommendation": {"verdict": "hire", "composite_score": 8.2},
        "hiring_decision": {"decision": "hire", "decision_score": 8.2},
    }
    aura = build_aura_from_state(state)
    assert aura["role_brain"]["seniority"] == "senior"
    assert aura["difficulty_state"]["role_floor"] == 3


def test_refresh_brain_layers_on_brain():
    from app.core.interview_brain import InterviewBrain

    brain = InterviewBrain(job_role="Senior Backend Engineer")
    brain.competency_taxonomy = BACKEND_TAXONOMY
    brain.required_competencies = ["tech_system_design"]
    brain.hypotheses = HYPOTHESES
    brain.evidence_store = STRONG_EVIDENCE
    brain.competency_summary = {"tech_system_design": {"evidence_count": 2, "gap": 0.0}}
    brain.difficulty_level = 3
    refresh_brain_layers(brain)
    assert brain.question_strategy is not None
    assert brain.uncertainty_map
    assert brain.role_brain is not None
    assert brain.competency_graph["nodes"]


def test_calibration_caps_hire_verdict_low_difficulty():
    """The calibration brain never lets a shallow interview be a hire — the
    calibrated verdict must downgrade strong_hire/hire below difficulty 3."""
    from app.brain.calibration import build_calibration_state

    shallow = build_calibration_state(
        hiring_recommendation={"verdict": "strong_hire", "composite_score": 8.8},
        difficulty_reached=1,
        role_floor=3,
        total_evidence=3,
        proof_ratio=0.3,
        resolved_ratio=0.5,
        serious_contradictions=0,
    )
    assert shallow["calibrated_verdict"] == "borderline"
    assert shallow["calibrated_score"] <= 7.0

    deep = build_calibration_state(
        hiring_recommendation={"verdict": "hire", "composite_score": 8.2},
        difficulty_reached=4,
        role_floor=3,
        total_evidence=15,
        proof_ratio=0.7,
        resolved_ratio=0.8,
        serious_contradictions=0,
    )
    assert deep["calibrated_verdict"] == "hire"
    assert deep["calibrated_score"] > 8.0


def test_apply_calibration_verdict_overrides_report_verdict():
    from app.engine.decision import apply_calibration_verdict

    state = {
        "aura_brain": {
            "calibration_state": {
                "calibrated_verdict": "borderline",
                "calibrated_score": 6.9,
            }
        },
        "hiring_decision": {"decision": "hire", "decision_score": 8.2, "confidence": 0.7},
    }
    out = apply_calibration_verdict(state)
    assert out["hiring_decision"]["decision"] == "borderline"
    assert out["hiring_decision"]["decision_score"] == 6.9
    assert out["hiring_decision"]["draft"] == "hire"
    assert out["hiring_decision"]["calibration_source"] == "aura_v5_calibration"


def test_apply_calibration_verdict_noop_without_calibration():
    from app.engine.decision import apply_calibration_verdict

    state = {
        "aura_brain": {},
        "hiring_decision": {"decision": "hire", "decision_score": 8.2},
    }
    assert apply_calibration_verdict(state) == state


def test_default_taxonomy_assembly_is_safe():
    brain = assemble_aura_brain(
        job_role="Software Engineer",
        taxonomy=COMPETENCY_TAXONOMY,
        required_competencies=[],
        hypotheses=[],
    )
    assert brain["competency_graph"]["nodes"]
    assert brain["role_brain"]["critical_competencies"]
    assert brain["question_strategy"]["question_strategy"]["mode"] in ("explore", "conclude")