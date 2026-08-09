"""Deterministic (no-LLM) v4 nodes: planner, hypothesis, evidence extraction,
reflection, routing, and the deterministic question fallbacks."""
from tests.conftest import make_v4_state

from app.agents.planning.action_router import route_after_planner
from app.agents.planning.competency_planner import competency_planner_node
from app.agents.reasoning.evidence_engine import evidence_extractor_node
from app.agents.reasoning.hypothesis_engine import hypothesis_node
from app.agents.generation.question_generator import (
    _count_competency_questions,
    _fallback_question,
    _generate_deterministic_question,
)
from app.agents.reasoning.reflection_engine import reflection_engine


async def test_competency_planner_produces_plan():
    state = await competency_planner_node(make_v4_state())
    assert isinstance(state["competency_plan"], list)
    assert state["competency_plan"]
    assert state["next_competency"] is not None
    assert state["planned_competency"] == state["next_competency"]["id"]
    assert "planner_sufficient" in state


async def test_hypothesis_node_seeds_hypothesis_for_planned_competency():
    state = make_v4_state(
        job_role="Backend Engineer",
        planned_competency="tech_db",
        last_hypothesis_target_id="h1",
        hypotheses=[{
            "id": "h1",
            "competency": "tech_core",
            "statement": "s",
            "direction": "positive",
            "confidence": 0.9,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "status": "confirmed",
        }],
    )
    result = await hypothesis_node(state)
    seeded = [h for h in result["hypotheses"] if h.get("competency") == "tech_db"]
    assert seeded and seeded[0]["status"] == "untested"
    assert result["hypothesis_target"]["competency"] == "tech_db"


async def test_hypothesis_node_saturation_seeds_target_instead_of_none():
    """Regression (Fix 11): when every hypothesis is settled, the node must
    seed a fresh hypothesis target — a null target caused premature finals."""
    state = make_v4_state(
        job_role="Backend Engineer",
        hypotheses=[{
            "id": "h1",
            "competency": "tech_core",
            "statement": "s",
            "direction": "positive",
            "confidence": 0.9,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "status": "confirmed",
        }],
    )
    result = await hypothesis_node(state)
    assert result["hypothesis_target"] is not None
    assert result["hypothesis_target"].get("competency") == "tech_core"


async def test_hypothesis_node_generates_initial_hypotheses():
    state = await hypothesis_node(make_v4_state(job_role="Backend Engineer"))
    assert state["hypotheses"]
    assert all(h.get("statement") for h in state["hypotheses"])
    assert all(h.get("competency") for h in state["hypotheses"])
    assert state["hypothesis_target"] is not None
    assert state["hypothesis_target"].get("id")


def test_hypotheses_map_skills_to_competency_ids():
    from app.agents.reasoning.hypothesis_engine import generate_initial_hypotheses

    hyps = generate_initial_hypotheses(
        "Backend Engineer",
        {"strengths": ["Python", "React"], "weaknesses": ["DevOps"]},
        max_hypotheses=20,
    )
    by_statement = {h["statement"]: h.get("competency") for h in hyps}
    assert by_statement.get("Candidate has strong Python") == "tech_core"
    assert by_statement.get("Candidate has strong React") == "tech_framework"
    assert by_statement.get("Candidate is weak in DevOps") == "tech_devops"
    assert by_statement.get("Candidate communicates clearly and effectively") == "behav_communication"


async def test_hypothesis_node_updates_with_evidence():
    from app.agents.reasoning.hypothesis_engine import generate_initial_hypotheses

    state = make_v4_state(job_role="Backend Engineer")
    hypotheses = generate_initial_hypotheses(
        state["job_role"], state["candidate_profile"], competency_taxonomy=state["competency_taxonomy"]
    )
    target = hypotheses[0]
    first_conf = target.get("confidence", 0.0)
    updated = await hypothesis_node({
        **state,
        "hypotheses": hypotheses,
        "extracted_evidence": [{
            "competency": target.get("competency", "tech_core"),
            "dimension": "technical",
            "score": 9.0,
            "confidence": 0.9,
            "evidence_text": "Strong answer",
        }],
    })
    assert updated["hypotheses"][0].get("confidence", 0.0) >= first_conf


async def test_evidence_extractor_skips_none_scores_and_sums_summary(fake_evidence_repo):
    state = await evidence_extractor_node(make_v4_state(
        question_number=1,
        current_question="Q1",
        question_objective={"target_competency": "tech_core"},
        unified_evaluation={
            "technical": {"score": 8.0, "evidence": "solid", "confidence": 0.9, "strengths": [], "weaknesses": []},
            "behavioral": {"score": None, "evidence": "n/a", "confidence": 0.0, "strengths": [], "weaknesses": []},
        },
    ))
    assert len(state["extracted_evidence"]) == 1
    assert state["extracted_evidence"][0]["dimension"] == "technical"
    summary = state["competency_summary"]["tech_core"]
    assert summary["evidence_count"] == 1
    assert summary["average_score"] == 8.0


async def test_reflection_engine_probes_on_fresh_state():
    state = await reflection_engine(make_v4_state(question_number=1))
    assert state["reflection_action"] == "probe"


async def test_reflection_engine_finishes_after_max_questions():
    state = await reflection_engine(make_v4_state(question_number=20))
    assert state["reflection_action"] == "finish"


async def test_reflection_engine_caps_at_fourteen_turns():
    """AURA cap: evidence-driven end usually fires earlier, but never past 14."""
    state = await reflection_engine(make_v4_state(question_number=14))
    assert state["reflection_action"] == "finish"


async def test_reflection_engine_switches_competency_on_two_contradictions():
    competency_summary = {
        "tech_core": {"scores": [8.0, 3.0], "evidence_count": 2, "average_score": 5.5, "gap": 0.5},
        "tech_db": {"scores": [9.0, 2.0], "evidence_count": 2, "average_score": 5.5, "gap": 0.5},
    }
    state = await reflection_engine(make_v4_state(question_number=4, competency_summary=competency_summary))
    assert len(state["contradictions"]) >= 2
    assert state["reflection_action"] == "change_competency"


# --------------------------------------------------------------------- #
# Fix 12 regressions: saturation must never finish on low coverage, the
# high-difficulty finish path must not crash, and the governor/generator
# must survive messy LLM output.
# --------------------------------------------------------------------- #

_REQUIRED_SIX = [
    "tech_core", "tech_db", "tech_system_design",
    "behav_communication", "cog_problem_solving", "exp_project_depth",
]

_COVERED = {"evidence_count": 2, "average_score": 8.0, "gap": 0.1, "average_confidence": 0.8}
_UNCOVERED = {"evidence_count": 0, "average_score": 0.0, "gap": 1.0, "average_confidence": 0.0}


def _settled_hypotheses() -> list[dict]:
    return [
        {
            "id": f"h{i}",
            "competency": comp,
            "statement": f"Candidate is strong in {comp}",
            "direction": "positive",
            "confidence": 0.8,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "status": "confirmed",
        }
        for i, comp in enumerate(_REQUIRED_SIX)
    ]


async def test_reflection_engine_rotates_on_saturation_with_low_coverage():
    """Regression: all hypotheses settled + only 2/6 competencies covered at
    question 5 must rotate (change_competency), never finish — finishing there
    produced a premature insufficient_evidence final verdict in the demo."""
    competency_summary = {
        "tech_core": dict(_COVERED),
        "tech_db": dict(_COVERED),
        "tech_system_design": dict(_UNCOVERED),
        "behav_communication": dict(_UNCOVERED),
        "cog_problem_solving": dict(_UNCOVERED),
        "exp_project_depth": dict(_UNCOVERED),
    }
    state = await reflection_engine(make_v4_state(
        question_number=5,
        required_competencies=_REQUIRED_SIX,
        hypotheses=_settled_hypotheses(),
        competency_summary=competency_summary,
    ))
    assert state["reflection_action"] == "change_competency"


async def test_reflection_engine_finishes_on_saturation_with_full_coverage():
    competency_summary = {comp: dict(_COVERED) for comp in _REQUIRED_SIX}
    state = await reflection_engine(make_v4_state(
        question_number=5,
        required_competencies=_REQUIRED_SIX,
        hypotheses=_settled_hypotheses(),
        competency_summary=competency_summary,
    ))
    assert state["reflection_action"] == "finish"


async def test_high_difficulty_finish_path_uses_computed_priority_ratio():
    """Regression: the top-difficulty finish branch referenced an undefined
    ``high_priority_ratio`` (NameError) — it must derive it from the
    evidence-sufficiency details instead."""
    from app.agents.reasoning.contradiction_engine import decide_next_action

    competency_summary = {comp: dict(_COVERED) for comp in _REQUIRED_SIX}
    evidence_sufficiency = {
        "is_sufficient": False,
        "coverage_ratio": 1.0,
        "details": {
            comp: {"covered": comp in ("tech_core", "tech_db", "tech_system_design")}
            for comp in _REQUIRED_SIX
        },
    }
    hypotheses = [
        {
            "id": "h-open",
            "competency": "tech_core",
            "statement": "s",
            "direction": "positive",
            "confidence": 0.5,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "status": "testing",
        }
    ]
    action = decide_next_action(
        competency_summary,
        _REQUIRED_SIX,
        evidence_sufficiency,
        [],
        question_number=5,
        hypotheses=hypotheses,
        difficulty_reached=5,
    )
    assert action == "finish"


async def test_high_difficulty_does_not_finish_with_uncovered_competencies():
    """Fix 12: high difficulty + partial coverage must NOT finish while the
    required competencies are still starved of evidence — the interview keeps
    probing (the hard question cap is the only escape)."""
    from app.agents.reasoning.contradiction_engine import decide_next_action

    competency_summary = {comp: dict(_UNCOVERED) for comp in _REQUIRED_SIX}
    evidence_sufficiency = {
        "is_sufficient": True,
        "coverage_ratio": 0.73,
        "details": {
            comp: {"covered": comp in ("tech_core", "tech_db", "tech_system_design")}
            for comp in _REQUIRED_SIX
        },
    }
    hypotheses = [
        {
            "id": f"h-{i}",
            "competency": "tech_core",
            "status": "untested",
        }
        for i in range(3)
    ]
    action = decide_next_action(
        competency_summary,
        _REQUIRED_SIX,
        evidence_sufficiency,
        [],
        question_number=6,
        hypotheses=hypotheses,
        difficulty_reached=5,
    )
    assert action == "probe"

    # ... and the hard cap is the only escape
    capped = decide_next_action(
        competency_summary,
        _REQUIRED_SIX,
        evidence_sufficiency,
        [],
        question_number=14,
        hypotheses=hypotheses,
        difficulty_reached=5,
    )
    assert capped == "finish"


def test_route_after_planner():
    assert route_after_planner({"hypothesis_target": {"id": "x"}}) == "question_subgraph"
    assert route_after_planner({"planned_competency": "tech_core"}) == "question_subgraph"
    assert route_after_planner({"next_competency": {"id": "tech_core"}}) == "question_subgraph"
    assert route_after_planner({"question_number": 3}) == "question_subgraph"
    assert route_after_planner({"question_number": 8}) == "finish"


def test_deterministic_question_templates_are_unique_per_followup():
    q0 = _generate_deterministic_question("tech_core", "SWE", 2, "", "Strong in X", "avg 7.0", {}, "friendly", 0)
    q1 = _generate_deterministic_question("tech_core", "SWE", 2, "", "Strong in X", "avg 7.0", {}, "friendly", 1)
    assert q0 != q1
    assert "tech_core" in q0.lower() or "skills" in q0.lower()


def test_fallback_question_mentions_competency_and_role():
    q = _fallback_question("tech_core", "Data Scientist", 2)
    assert "Data Scientist" in q
    assert "tech core" in q


def test_count_competency_questions():
    questions = [
        {"competency": "tech_core"},
        {"competency": "tech_db"},
        {"competency": "tech_core"},
    ]
    assert _count_competency_questions(questions, "tech_core") == 2
    assert _count_competency_questions([], "tech_core") == 0


# --------------------------------------------------------------------- #
# Governor JSON resilience + generator fallback regressions (Fix 12)
# --------------------------------------------------------------------- #


async def test_govern_difficulty_parses_messy_llm_json(stub_llm):
    """Regression: cheap-tier LLM output with text after the JSON object (or
    wrapped in a fence) crashed the naive json.loads and disabled the
    governor — it must parse either shape."""
    from app.engine.routing import govern_difficulty

    stub_llm(responses=[
        '{"delta": 1, "rationale": "kept up", "scaffold": ""}\nSome extra explanatory text.',
        '```json\n{"delta": -1, "rationale": "too hard", "scaffold": ""}\n```',
    ])

    up = await govern_difficulty(make_v4_state(question_number=3), 3)
    assert up["difficulty_level"] == 2

    down = await govern_difficulty(make_v4_state(question_number=3, difficulty_level=4), 3)
    assert down["difficulty_level"] == 3


async def test_question_generator_uses_next_competency_when_target_missing(stub_llm):
    """Regression: without hypothesis/planned_competency, the objective must
    fall back to the planner's next_competency instead of degrading to
    'general' (which misattributed all evidence)."""
    from app.agents.generation.question_generator import question_generator_node

    stub_llm(response="Question: Walk me through a database-heavy project you shipped.")
    state = await question_generator_node(make_v4_state(next_competency={"id": "tech_db"}))
    assert state["question_objective"]["target_competency"] == "tech_db"
    assert state["questions_asked"][-1]["competency"] == "tech_db"


async def test_question_generator_final_fallback_skips_rejected_templates(monkeypatch):
    """Regression: when every attempt is rejected, the final deterministic
    fallback must not repeat a rejected template."""
    import app.agents.generation.question_generator as qg

    monkeypatch.setattr(
        qg.QuestionSimilarityGuard, "is_duplicate",
        lambda self, text, memory: (True, {"kind": "forced"}),
    )

    async def _fail(*args, **kwargs):
        raise RuntimeError("stub LLM failure")

    monkeypatch.setattr(qg, "_generate_llm_question", _fail)

    state = await qg.question_generator_node(make_v4_state())
    expected = qg._fallback_question("general", "Software Engineer", 1, variant=0)
    assert state["current_question"] == expected
    assert state["current_question"] not in qg._get_template_for_competency("general", "Software Engineer", 1)


async def test_question_generator_never_repeats_last_question(monkeypatch):
    """B1 regression: even when the mode-aware guard is bypassed (or the LLM
    echoes the previous question verbatim), the emitted question must never be
    byte-identical to the one just asked (Q13 == Q14)."""
    import app.agents.generation.question_generator as qg

    last = qg._fallback_question("general", "Software Engineer", 1, variant=3)
    monkeypatch.setattr(
        qg.QuestionSimilarityGuard, "is_duplicate",
        lambda self, text, memory: (False, {}),  # guard lets everything through
    )
    monkeypatch.setattr(qg, "_generate_llm_question", lambda **kw: last)

    state = await qg.question_generator_node(make_v4_state(
        difficulty_level=1,
        questions_asked=[
            {"id": "q12", "text": "An earlier question.", "competency": "tech_core"},
            {"id": "q13", "text": last, "competency": "tech_core"},
        ],
    ))
    assert state["current_question"] != last
    assert state["questions_asked"][-1]["text"] == state["current_question"]


async def test_question_generator_guard_is_mode_aware(stub_llm, monkeypatch):
    """EXPLORER (new competency) questions must be checked against ALL prior
    questions with a stricter bar; PROBER follow-ups only against their own
    competency's questions."""
    import app.agents.generation.question_generator as qg

    captured = {}

    class SpyingGuard(qg.QuestionSimilarityGuard):
        def is_duplicate(self, new_question, previous_questions):
            captured["memory"] = list(previous_questions)
            captured["threshold"] = self.similarity_threshold
            return False, {}

    monkeypatch.setattr(qg, "QuestionSimilarityGuard", SpyingGuard)
    stub_llm(response="Question: A brand new angle.")

    explorer = await qg.question_generator_node(make_v4_state(
        next_competency={"id": "tech_framework"},
        questions_asked=[
            {"id": "q1", "text": "Tell me about model accuracy metrics.", "competency": "tech_core"},
        ],
    ))
    assert explorer["question_objective"]["target_competency"] == "tech_framework"
    assert captured["threshold"] == 0.78
    assert captured["memory"] == ["Tell me about model accuracy metrics."]

    captured.clear()
    stub_llm(response="Question: Another fresh angle.")
    await qg.question_generator_node(make_v4_state(
        hypothesis_target={"id": "h1", "competency": "tech_core"},
        competency_summary={"tech_core": {"evidence_count": 1}},
        questions_asked=[
            {"id": "q1", "text": "Tech core question one.", "competency": "tech_core"},
            {"id": "q2", "text": "Framework question.", "competency": "tech_framework"},
        ],
    ))
    assert captured["threshold"] == 0.85
    assert captured["memory"] == ["Tech core question one."]


def test_refresh_target_reference_repoints_stale_target():
    """Regression: the evaluator replaces hypothesis dicts with copies every
    turn, leaving ``hypothesis_target`` pointing at pre-evaluation status.
    The refresh must re-point it at the live object so the director reads
    fresh confidence/status."""
    from app.core.interview_brain import InterviewBrain
    from app.engine.routing import _refresh_target_reference

    stale = {
        "id": "h1",
        "competency": "tech_core",
        "status": "untested",
        "confidence": 0.0,
    }
    live = {
        "id": "h1",
        "competency": "tech_core",
        "status": "testing",
        "confidence": 0.8239,
        "supporting_evidence": ["e1"],
        "contradicting_evidence": [],
    }
    brain = InterviewBrain(hypotheses=[live], hypothesis_target=stale)

    _refresh_target_reference(brain)

    assert brain.hypothesis_target is live
    assert brain.hypothesis_target["status"] == "testing"


def test_director_probes_after_target_refresh():
    """Regression: with the target refreshed post-evaluation, a testing belief
    at 0.82 confidence must yield PROBE → deep_probe, not CONTINUE."""
    from app.agents.decision.director import director_controller

    state = {
        "reflection_action": "probe",
        "evidence_sufficiency": {},
        "contradictions": [],
        "question_number": 2,
        "max_questions": 14,
        "consecutive_probes": 0,
        "last_hypothesis_target_id": "",
        "difficulty_level": 2,
        "evaluation_score": 8.0,
        "hypothesis_target": {
            "id": "h1",
            "competency": "tech_core",
            "status": "testing",
            "confidence": 0.8239,
        },
    }

    decision = director_controller(state)

    assert decision["action"] == "PROBE"
    assert decision["probe_mode"] == "deep_probe"


def test_director_projects_pending_evidence_before_deciding():
    """Regression: pending extracted_evidence must be applied to the target
    BEFORE the director decides (hypothesis_node does the real update only
    after the director runs), so a follow-up on a just-supported belief flips
    to PROBE → deep_probe instead of CONTINUE → explore_new_competency."""
    from app.agents.decision.director import director_controller
    from app.engine.routing import _project_target_evidence

    state = {
        "reflection_action": "probe",
        "evidence_sufficiency": {},
        "contradictions": [],
        "question_number": 1,
        "max_questions": 14,
        "consecutive_probes": 0,
        "last_hypothesis_target_id": "",
        "difficulty_level": 1,
        "evaluation_score": 8.0,
        "hypothesis_target": {
            "id": "h1",
            "competency": "tech_core",
            "statement": "Candidate has strong technical depth in Python",
            "direction": "positive",
            "confidence": 0.5,
            "probability": 0.5,
            "status": "untested",
            "evidence_count": 0,
            "required_evidence": 2,
        },
        "extracted_evidence": [
            {
                "id": "e1",
                "competency": "tech_core",
                "dimension": "communication",
                "score": 8.0,
                "confidence": 0.9,
                "evidence_text": "Well-structured response with clear explanation flow",
            }
        ],
    }

    projected = _project_target_evidence(state)
    assert projected["hypothesis_target"]["status"] == "testing"
    assert projected["hypothesis_target"]["confidence"] > 0.7

    decision = director_controller(projected)
    assert decision["action"] == "PROBE"
    assert decision["probe_mode"] == "deep_probe"

    no_evidence = {**state, "extracted_evidence": []}
    decision_no_evidence = director_controller(_project_target_evidence(no_evidence))
    assert decision_no_evidence["action"] == "CONTINUE"

    # The projection must not mutate the caller's state.
    assert state["hypothesis_target"]["status"] == "untested"


def test_company_context_is_mode_aware():
    """Only the first question of a competency (EXPLORER mode) gets company
    grounding; follow-up modes get N/A."""
    from app.agents.generation.question_generator import _company_context

    state = {
        "company_brain": {
            "company_vision": "Ship reliable software",
            "tech_stack": ["k8s"],
        }
    }
    assert "Ship reliable software" in _company_context(state, "EXPLORER")
    assert _company_context(state, "PROBER") == "N/A"
    assert _company_context(state, "CHALLENGER") == "N/A"
    assert _company_context(state, "VERIFIER") == "N/A"
    assert _company_context(state, "CLOSER") == "N/A"
    assert "Ship reliable software" in _company_context(state)
