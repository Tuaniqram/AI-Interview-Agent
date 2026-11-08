"""Plan step 4: substantiation caps the competency score, answer_signals per answer,
and competency ids resolve to their family even when the session taxonomy omits them."""
from app.agents.evaluation.scoring import UNSUBSTANTIATED_SCORE_CAP, competency_score
from app.agents.reasoning.evidence_engine import (
    build_candidate_evidence,
    evidence_extractor_node,
    unsubstantiated_share,
)
from app.data.rubrics import category_from_taxonomy
from tests.conftest import make_v4_state

EVAL = {
    "technical": {"score": 9.0, "confidence": 0.9, "evidence": "We cut latency by 92% across the platform.",
                  "strengths": [], "weaknesses": []},
    "reasoning": {"score": 8.0, "confidence": 0.8, "evidence": "It was the obvious choice.", "strengths": [], "weaknesses": []},
    "completeness": {"score": 8.0, "confidence": 0.8, "evidence": "Covered it.", "strengths": [], "weaknesses": []},
}
UNSUB = {"substantiation": {"verifiable": False, "specifics": [], "unsupported_claims": ["cut latency by 92%"]}}


def test_unverifiable_with_unsupported_claims_caps_at_5_5():
    assert competency_score(EVAL, "technical") > 8.0
    assert competency_score(EVAL, "technical", UNSUB) == UNSUBSTANTIATED_SCORE_CAP == 5.5


def test_unverifiable_without_claims_is_not_capped():
    extras = {"substantiation": {"verifiable": False, "specifics": [], "unsupported_claims": []}}
    assert competency_score(EVAL, "technical", extras) > 8.0


def test_cap_never_raises_a_low_score():
    low = {"technical": {"score": 3.0, "confidence": 0.9, "evidence": "x"}}
    assert competency_score(low, "technical", UNSUB) == 3.0


def test_evidence_record_carries_capped_score():
    records = build_candidate_evidence(
        evaluation=EVAL, question="Q", question_number=2, session_id="s1",
        question_objective={"target_competency": "tech_core"}, extras=UNSUB,
    )
    assert records and all(r["score"] == 5.5 for r in records)


async def test_extractor_appends_one_answer_signal_per_question(fake_evidence_repo):
    state = make_v4_state(
        question_number=3, current_question="Q3", candidate_answer="We cut latency by 92%.",
        question_objective={"target_competency": "tech_core"},
        unified_evaluation=EVAL,
        unified_evaluation_extras={**UNSUB, "admitted_gap": False, "asked_interviewer": True},
    )
    state = await evidence_extractor_node(state)
    state = await evidence_extractor_node(state)  # a re-run replaces, never double-counts
    signals = state["answer_signals"]
    assert len(signals) == 1
    sig = signals[0]
    assert sig["question_number"] == 3 and sig["competency"] == "tech_core"
    assert sig["competency_score"] == 5.5
    assert sig["verifiable"] is False and sig["unsupported_claims"] == ["cut latency by 92%"]
    assert sig["asked_interviewer"] is True and sig["admitted_gap"] is False


def test_unsubstantiated_share():
    assert unsubstantiated_share([]) is None
    assert unsubstantiated_share([{"verifiable": False}, {"verifiable": True}, {"verifiable": True},
                                  {"verifiable": False}]) == 0.5


def test_category_falls_back_to_id_prefix():
    session = [{"id": "tech_core", "category": "technical"}]
    assert category_from_taxonomy(session, "tech_core") == "technical"
    assert category_from_taxonomy(session, "behav_communication") == "behavioral"
    assert category_from_taxonomy([{"id": "behav_teamwork"}], "behav_teamwork") == "behavioral"
    assert category_from_taxonomy(None, "cog_analytical") == "cognitive"
    assert category_from_taxonomy(session, "custom_thing") is None
    # an explicit session category still wins
    assert category_from_taxonomy([{"id": "behav_x", "category": "commerce"}], "behav_x") == "commerce"
