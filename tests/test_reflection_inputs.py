"""Reflection engine inputs: coverage, evidence confidence, difficulty reached,
unanswered hypotheses, and remaining budget."""
from tests.conftest import make_v4_state

from app.agents.reasoning.contradiction_engine import (
    MAX_QUESTIONS_PER_COMPETENCY,
    average_evidence_confidence,
    competency_question_counts,
    decide_next_action,
    evaluate_sufficiency,
    unanswered_hypothesis_count,
)
from app.agents.reasoning.reflection_engine import reflection_engine


def _summary(entries):
    return {
        comp: {
            "evidence_count": e,
            "average_score": s,
            "average_confidence": c,
            "gap": g,
            "scores": [s] * e,
        }
        for comp, (e, s, c, g) in entries.items()
    }


def test_average_confidence_is_evidence_count_weighted():
    summary = _summary({
        "tech_core": (2, 8.0, 0.9, 0.1),
        "tech_db": (1, 6.0, 0.3, 0.4),
    })
    assert average_evidence_confidence(summary) == 0.7
    assert average_evidence_confidence({}) == 0.0


def test_unanswered_hypothesis_count():
    hyps = [
        {"status": "untested"},
        {"status": "testing"},
        {"status": "confirmed"},
        {"status": "refuted"},
    ]
    assert unanswered_hypothesis_count(hyps) == 2


def test_evaluate_sufficiency_temperes_confidence_with_evidence_quality():
    summary = _summary({
        "tech_core": (3, 8.0, 0.4, 0.1),
        "tech_db": (3, 7.5, 0.4, 0.1),
    })
    sufficiency, rec = evaluate_sufficiency(
        summary,
        ["tech_core", "tech_db"],
        [],
        [{"status": "confirmed"}, {"status": "confirmed"}],
        question_number=6,
        comp_weights={"tech_core": 1.0, "tech_db": 1.0},
    )
    assert sufficiency["average_confidence"] == 0.4
    assert rec["average_confidence"] == 0.4
    assert sufficiency["is_sufficient"] is True
    # confidence = min(confirmed/(confirmed+refuted+1) * max(0.4, 0.5), 0.95)
    assert rec["confidence"] == round(2 / 3 * 0.5, 2)


def test_evaluate_sufficiency_records_difficulty_and_unanswered():
    summary = _summary({"tech_core": (2, 7.0, 0.8, 0.1)})
    sufficiency, rec = evaluate_sufficiency(
        summary,
        ["tech_core"],
        [],
        [],
        question_number=3,
        comp_weights={"tech_core": 1.0},
        difficulty_reached=3,
        unanswered_hypotheses=5,
    )
    assert sufficiency["difficulty_reached"] == 3
    assert sufficiency["unanswered_hypotheses"] == 5
    assert rec["difficulty_reached"] == 3


def test_decide_next_action_finishes_at_top_difficulty_with_coverage():
    """V5: even top difficulty needs >=80% coverage breadth to finish."""
    sufficiency = {"is_sufficient": False, "coverage_ratio": 0.85}
    action = decide_next_action(
        {}, [], sufficiency, [], question_number=6, hypotheses=[],
        difficulty_reached=5,
    )
    assert action == "finish"


def test_decide_next_action_blocks_finish_below_80_percent_coverage():
    """The demo regression: top difficulty alone must not end a senior
    interview on 75% (half a blueprint untested)."""
    sufficiency = {"is_sufficient": False, "coverage_ratio": 0.75}
    action = decide_next_action(
        {}, [], sufficiency, [], question_number=6, hypotheses=[],
        difficulty_reached=5,
    )
    assert action == "probe"


def test_decide_next_action_probes_at_top_difficulty_without_coverage():
    sufficiency = {"is_sufficient": False, "coverage_ratio": 0.4}
    action = decide_next_action(
        {}, [], sufficiency, [], question_number=6, hypotheses=[],
        difficulty_reached=3,
    )
    assert action == "probe"


def test_decide_next_action_ignores_difficulty_before_question_five():
    sufficiency = {"is_sufficient": False, "coverage_ratio": 0.8}
    action = decide_next_action(
        {}, [], sufficiency, [], question_number=3, hypotheses=[],
        difficulty_reached=3,
    )
    assert action == "probe"


def test_decide_next_action_rotates_when_all_hypotheses_settled():
    sufficiency = {"is_sufficient": False, "coverage_ratio": 0.0}
    hyps = [
        {"status": "confirmed"},
        {"status": "refuted"},
        {"status": "confirmed"},
    ]
    action = decide_next_action(
        {}, ["tech_core"], sufficiency, [], question_number=4, hypotheses=hyps,
    )
    assert action == "change_competency"


def test_decide_next_action_rotates_when_competency_covered():
    summary = {"tech_core": {"evidence_count": 2, "gap": 0.0}}
    sufficiency = {"is_sufficient": False, "coverage_ratio": 0.5}
    action = decide_next_action(
        summary, ["tech_core", "tech_db"], sufficiency, [],
        question_number=4, hypotheses=[{"status": "testing"}],
    )
    assert action == "change_competency"


def test_decide_next_action_keeps_probing_when_only_competency_covered():
    summary = {"tech_core": {"evidence_count": 2, "gap": 0.0}}
    sufficiency = {"is_sufficient": False, "coverage_ratio": 1.0}
    action = decide_next_action(
        summary, ["tech_core"], sufficiency, [],
        question_number=4, hypotheses=[{"status": "testing"}],
    )
    assert action == "probe"


def test_competency_question_counts_counts_asked_questions():
    counts = competency_question_counts([
        {"competency": "tech_core"},
        {"competency": "tech_db"},
        {"competency": "tech_core"},
        {},
        {"competency": "tech_core"},
    ])
    assert counts == {"tech_core": 3, "tech_db": 1}
    assert competency_question_counts([]) == {}


def test_decide_next_action_rotates_away_from_capped_competency():
    sufficiency = {"is_sufficient": False, "coverage_ratio": 0.5}
    action = decide_next_action(
        {}, ["tech_core", "tech_db"], sufficiency, [], question_number=4,
        hypotheses=[{"status": "testing"}],
        question_counts={"tech_core": MAX_QUESTIONS_PER_COMPETENCY, "tech_db": 1},
        last_competency="tech_core",
    )
    assert action == "change_competency"


def test_decide_next_action_does_not_rotate_before_cap():
    sufficiency = {"is_sufficient": False, "coverage_ratio": 0.5}
    action = decide_next_action(
        {}, ["tech_core", "tech_db"], sufficiency, [], question_number=4,
        hypotheses=[{"status": "testing"}],
        question_counts={"tech_core": 2, "tech_db": 0},
        last_competency="tech_core",
    )
    assert action != "change_competency"


def test_decide_next_action_never_finishes_before_question_five():
    """Fix 11: even a fully sufficient profile cannot end the interview before
    the minimum question count — a hiring decision needs an evidence base."""
    summary = _summary({
        "tech_core": (2, 8.0, 0.9, 0.0),
        "tech_db": (2, 7.5, 0.9, 0.0),
    })
    sufficiency, _ = evaluate_sufficiency(
        summary,
        ["tech_core", "tech_db"],
        [],
        [{"status": "confirmed"}, {"status": "confirmed"}],
        question_number=6,
        comp_weights={"tech_core": 1.0, "tech_db": 1.0},
    )
    assert sufficiency["is_sufficient"] is True
    action = decide_next_action(
        summary, ["tech_core", "tech_db"], sufficiency, [], question_number=3,
        hypotheses=[{"status": "confirmed"}, {"status": "confirmed"}],
    )
    assert action == "probe"


def test_decide_next_action_finishes_when_required_fully_covered():
    sufficiency = {"is_sufficient": False, "coverage_ratio": 1.0}
    summary = {
        "tech_core": {"evidence_count": 2, "gap": 0.0, "average_confidence": 0.8},
        "tech_db": {"evidence_count": 2, "gap": 0.0, "average_confidence": 0.8},
    }
    action = decide_next_action(
        summary, ["tech_core", "tech_db"], sufficiency, [], question_number=6,
        hypotheses=[
            {"competency": "tech_core", "status": "confirmed"},
            {"competency": "tech_db", "status": "refuted"},
        ],
    )
    assert action == "finish"


def test_decide_next_action_keeps_probing_when_required_open_hypothesis_exists():
    sufficiency = {"is_sufficient": False, "coverage_ratio": 1.0}
    summary = {
        "tech_core": {"evidence_count": 2, "gap": 0.0, "average_confidence": 0.8},
        "tech_db": {"evidence_count": 2, "gap": 0.0, "average_confidence": 0.8},
    }
    action = decide_next_action(
        summary, ["tech_core", "tech_db"], sufficiency, [], question_number=6,
        hypotheses=[
            {"competency": "tech_core", "status": "confirmed"},
            {"competency": "tech_db", "status": "testing"},
        ],
    )
    assert action != "finish"


def test_decide_next_action_finishes_on_saturation_regardless_of_confidence():
    """Design contract (Phase B): once every hypothesis is settled and the
    required competencies are covered, the interview finishes — confidence is
    a verdict-quality signal handled by the decision engine, not a
    stop-probing gate here."""
    sufficiency = {"is_sufficient": False, "coverage_ratio": 1.0}
    summary = {
        "tech_core": {"evidence_count": 2, "gap": 0.0, "average_confidence": 0.4},
        "tech_db": {"evidence_count": 2, "gap": 0.0, "average_confidence": 0.4},
    }
    action = decide_next_action(
        summary, ["tech_core", "tech_db"], sufficiency, [], question_number=6,
        hypotheses=[
            {"competency": "tech_core", "status": "confirmed"},
            {"competency": "tech_db", "status": "refuted"},
        ],
    )
    assert action == "finish"


async def test_reflection_engine_rotates_on_capped_competency():
    questions = [{"competency": "tech_core"} for _ in range(MAX_QUESTIONS_PER_COMPETENCY)]
    state = await reflection_engine(make_v4_state(
        question_number=5,
        difficulty_level=2,
        questions_asked=questions,
        hypotheses=[
            {"id": "h1", "competency": "tech_core", "statement": "s", "direction": "positive",
             "confidence": 0.5, "supporting_evidence": [], "contradicting_evidence": [],
             "status": "testing"},
            {"id": "h2", "competency": "tech_db", "statement": "s", "direction": "positive",
             "confidence": 0.5, "supporting_evidence": [], "contradicting_evidence": [],
             "status": "untested"},
        ],
    ))
    assert state["reflection_action"] == "change_competency"


async def test_reflection_engine_surfaces_inputs():
    state = await reflection_engine(make_v4_state(question_number=4, difficulty_level=2))
    inputs = state["reflection_inputs"]
    assert "coverage_ratio" in inputs
    assert "average_confidence" in inputs
    assert inputs["difficulty_reached"] == 2
    assert "unanswered_hypotheses" in inputs
    assert inputs["budget_remaining"] == 10
    assert "contradiction_count" in inputs


async def test_reflection_engine_reports_unanswered_hypotheses():
    hypotheses = [
        {"id": "h1", "competency": "tech_core", "statement": "s", "direction": "positive",
         "confidence": 0.4, "supporting_evidence": [], "contradicting_evidence": [],
         "status": "testing"},
        {"id": "h2", "competency": "tech_core", "statement": "s", "direction": "positive",
         "confidence": 0.9, "supporting_evidence": [], "contradicting_evidence": [],
         "status": "confirmed"},
    ]
    state = await reflection_engine(make_v4_state(
        question_number=4, difficulty_level=2, hypotheses=hypotheses,
    ))
    assert state["reflection_inputs"]["unanswered_hypotheses"] == 1
    assert state["hiring_recommendation"]["unanswered_hypotheses"] == 1
