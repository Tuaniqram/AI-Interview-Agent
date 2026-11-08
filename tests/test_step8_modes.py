"""Plan step 8: challenge only after real depth, one fundamentals step after an admitted gap, better fallbacks."""
from app.agents.decision.director import director_controller
from app.agents.generation.question_generator import (
    _cv_anchor,
    _generate_deterministic_question,
    question_generator_node,
)
from tests.conftest import CONDUCTOR_TURN_JSON, make_v4_state


def _director_state(**overrides):
    state = {
        "reflection_action": "change_competency", "evidence_sufficiency": {}, "question_number": 5,
        "max_questions": 14, "consecutive_probes": 0, "last_hypothesis_target_id": "", "difficulty_level": 2,
        "evaluation_score": 3.0,
        "hypothesis_target": {"id": "h1", "competency": "tech_db", "status": "testing", "confidence": 0.4},
        "contradiction_state": {"contradictions": [], "needs_challenge": False},
        "answer_signals": [{"question_number": 5, "competency": "tech_db", "admitted_gap": True}],
        "questions_asked": [{"mode": "PROBER", "competency": "tech_db"}] * 5,
    }
    state.update(overrides)
    return state


def test_admitted_gap_gives_one_step_down_then_change_competency():
    first = director_controller(_director_state())
    assert first["action"] == "PROBE" and first["probe_mode"] == "step_down"
    # the fundamentals question was asked (competency recorded) and answered: move on, even after another gap
    after = director_controller(_director_state(
        question_number=6,
        scaffolded_competencies=["tech_db"],
        answer_signals=[{"question_number": 6, "competency": "tech_db", "admitted_gap": True}],
        questions_asked=[{"mode": "PROBER"}] * 5 + [{"mode": "SCAFFOLD", "competency": "tech_db"}],
    ))
    assert after["action"] == "CHANGE_COMPETENCY"
    assert "fundamentals" in after["reason"]


def test_no_step_down_without_a_gap_on_the_latest_answer():
    stale = director_controller(_director_state(
        answer_signals=[{"question_number": 4, "competency": "tech_db", "admitted_gap": True}],
    ))
    assert stale["probe_mode"] != "step_down"
    no_gap = director_controller(_director_state(
        answer_signals=[{"question_number": 5, "competency": "tech_db", "admitted_gap": False}],
    ))
    assert no_gap["probe_mode"] != "step_down"


def test_a_claim_conflict_is_reconciled_before_the_step_down():
    conflict = {"id": "c1", "status": "open", "kind": "changed_value", "metric_key": "x",
                "first": {"question_number": 2, "value_text": "1%"}, "second": {"question_number": 5, "value_text": "9%"}}
    decision = director_controller(_director_state(claim_conflicts=[conflict]))
    assert decision["probe_mode"] == "reconcile_claim"


async def test_scaffold_question_is_easier_on_the_same_competency(stub_llm):
    stub = stub_llm(response=CONDUCTOR_TURN_JSON)
    out = await question_generator_node(make_v4_state(
        persona="conductor", question_number=5, difficulty_level=4,
        director={"action": "PROBE", "probe_mode": "step_down"},
        hypothesis_target={"id": "h9", "competency": "tech_core", "status": "testing"},
        answer_signals=[{"question_number": 5, "competency": "tech_db", "admitted_gap": True}],
    ))
    assert out["interview_mode"] == "SCAFFOLD"
    assert out["question_objective"]["target_competency"] == "tech_db"
    assert out["question_objective"]["difficulty"] == 2
    assert out["difficulty_level"] == 4  # the session level is unchanged
    assert out["scaffolded_competencies"] == ["tech_db"]
    prompt = stub.calls[0]["prompt"]
    assert "**Admitted Gap On Last Answer**: yes" in prompt
    assert "**Difficulty Level**: 2/5" in prompt


def test_deterministic_scaffold_question_is_fundamentals_level():
    q = _generate_deterministic_question(
        target_competency="tech_db", job_role="Backend Developer", difficulty=2, approach="",
        hypothesis_text="", competency_info="", candidate_profile={}, persona="conductor",
        followup_number=1, interview_mode="SCAFFOLD",
    )
    assert "simpler angle" in q and "challenge" not in q.lower()


def test_cv_anchor_and_role_floor_phrasing():
    state = {"candidate_brain": {"skills": ["Python", "PostgreSQL", "Docker"]}}
    assert _cv_anchor(state, "tech_db") == "PostgreSQL"
    assert _cv_anchor(state, "tech_devops") == "Docker"
    assert _cv_anchor(state, "behav_teamwork") == ""
    q = _generate_deterministic_question(
        target_competency="tech_db", job_role="Backend Developer", difficulty=1, approach="",
        hypothesis_text="", competency_info="", candidate_profile={}, persona="conductor",
        followup_number=0, interview_mode="EXPLORER", cv_anchor="PostgreSQL",
    )
    assert q.startswith("You list PostgreSQL on your CV.") and "Database" not in q
    junior = _generate_deterministic_question(
        target_competency="tech_db", job_role="Backend Developer", difficulty=1, approach="",
        hypothesis_text="Candidate may have gaps in databases", competency_info="", candidate_profile={},
        persona="conductor", followup_number=0, interview_mode="PROBER", role_floor=1,
    )
    assert "significant challenge" not in junior


async def test_question_source_is_recorded(stub_llm):
    stub_llm(response=CONDUCTOR_TURN_JSON)
    llm = await question_generator_node(make_v4_state(persona="conductor", question_number=3))
    assert llm["questions_asked"][-1]["question_source"] == "llm"
    stub_llm(fail=True)
    fallback = await question_generator_node(make_v4_state(persona="conductor", question_number=3))
    assert fallback["questions_asked"][-1]["question_source"] == "template"
    assert "_source" not in (fallback["conversation_turn"] or {})


def test_strategy_mode_follows_the_competency_being_asked():
    from app.brain.question_planner import generate_question_strategy

    umap = {
        "tech_system_design": {"uncertainty": 0.9, "importance": 3, "missing_evidence": ["x"]},
        "tech_db": {"uncertainty": 0.3, "importance": 2, "missing_evidence": []},
    }
    hyp = [{"competency": "tech_system_design", "status": "untested"}, {"competency": "tech_db", "status": "testing"}]
    cs = {"needs_challenge": False, "contradictions": [], "seniority_risk": {"level": "low", "action": "validate"}}
    ranked = generate_question_strategy(uncertainty_map=umap, contradiction_state=cs, hypothesis_brain=hyp)
    assert ranked["question_strategy"]["target_competency"] == "tech_system_design"
    asked = generate_question_strategy(uncertainty_map=umap, contradiction_state=cs, hypothesis_brain=hyp,
                                       target_competency="tech_db")
    assert asked["question_strategy"]["target_competency"] == "tech_db"
    assert asked["question_strategy"]["mode"] == "verify"  # tech_db's own mode, not the top competency's "explore"
    assert asked["planned_competency"] == "tech_system_design"  # the ranked choice is kept
