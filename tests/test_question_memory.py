"""V5 question memory & interview modes: duplicate prevention (Fix 3),
depth-mode wiring into the generator (Fix 4). No LLM required."""
from tests.conftest import make_v4_state

from app.agents.generation.question_generator import (
    _apply_mode_flavor,
    _claim_targets,
    _resolve_interview_mode,
    question_generator_node,
)
from app.agents.generation.question_memory import (
    avoid_topics_summary,
    check_duplicate,
    match_topics,
    recent_memory,
    semantic_similarity,
)
from app.agents.generation.question_similarity_guard import QuestionSimilarityGuard


def test_semantic_similarity_identical_is_one():
    assert semantic_similarity("How do you scale a database?", "How do you scale a database?") == 1.0


def test_semantic_similarity_unrelated_is_low():
    assert semantic_similarity("How do you scale a database?", "Tell me about a hobby you enjoy.") < 0.5


def test_check_duplicate_rejects_near_verbatim():
    dup, detail = check_duplicate(
        "How do you handle scalability challenges with LLMs at high volume?",
        ["How do you handle scalability challenges with LLMs at high volume?"],
    )
    assert dup
    assert detail["kind"] == "similar"
    assert detail["similarity"] > 0.8


def test_check_duplicate_rejects_topic_repeat():
    memory = ["How do you scale your LLM service for production volume and latency?"]
    dup, detail = check_duplicate("How does your team handle high traffic and model latency?", memory)
    assert dup
    assert detail["kind"] == "topic_repeat"
    assert "scalability" in detail["topics"] and "performance" in detail["topics"]


def test_check_duplicate_accepts_new_question():
    dup, detail = check_duplicate(
        "How do you handle database index strategy?",
        ["How do you scale your LLM service for production volume and latency?"],
    )
    assert not dup
    assert detail == {}


def test_check_duplicate_accepts_single_topic_overlap():
    dup, _ = check_duplicate(
        "What is your database schema migration strategy?",
        ["How do you scale your database for high volume?"],
    )
    assert not dup


def test_similarity_guard_rejects_near_duplicate():
    guard = QuestionSimilarityGuard(similarity_threshold=0.8)
    dup, detail = guard.is_duplicate(
        "How do you handle scalability challenges with LLMs at high volume?",
        ["How do you handle scalability challenges with LLMs at high volume?"],
    )
    assert dup
    assert detail["kind"] == "similar"
    assert detail["similarity"] >= 0.8


def test_similarity_guard_rejects_topic_repeat():
    guard = QuestionSimilarityGuard(similarity_threshold=0.8)
    dup, detail = guard.is_duplicate(
        "How does your team handle high traffic and model latency?",
        ["How do you scale your LLM service for production volume and latency?"],
    )
    assert dup
    assert detail["kind"] == "topic_repeat"
    assert "scalability" in detail["topics"] and "performance" in detail["topics"]


def test_recent_memory_caps_at_ten():
    questions = [{"text": f"q{i}"} for i in range(15)]
    memory = recent_memory(questions)
    assert len(memory) == 10
    assert memory[0] == "q5"


def test_recent_memory_skips_empty():
    questions = [{"text": ""}, {"text": "real"}, {}]
    assert recent_memory(questions) == ["real"]


def test_avoid_topics_summary_lists_covered_topics():
    summary = avoid_topics_summary(["How do you scale your LLM service at high volume?"])
    assert "scalability" in summary


def test_match_topics():
    assert match_topics("Describe the caching strategy with Redis invalidation") == {"caching"}
    assert match_topics("plain question") == set()


def test_mode_flavor_unchanged_for_explorer():
    base = "Tell me about your experience."
    assert _apply_mode_flavor(base, "EXPLORER", "tech_core") == base


def test_mode_flavor_adds_tradeoffs_for_challenger():
    flavored = _apply_mode_flavor("Design a scalable system.", "CHALLENGER", "tech_core")
    assert "trade-offs" in flavored


def test_mode_flavor_asks_for_measurement_for_verifier():
    flavored = _apply_mode_flavor("Describe your caching solution.", "VERIFIER", "tech_core")
    assert "measured" in flavored


def test_resolve_interview_mode_from_director_probe_mode():
    state = make_v4_state(director={"probe_mode": "deep_probe"})
    assert _resolve_interview_mode(state) == "PROBER"
    state = make_v4_state(director={"probe_mode": "challenge_candidate"})
    assert _resolve_interview_mode(state) == "CHALLENGER"


def test_resolve_interview_mode_from_v5_brain_strategy():
    from app.brain.question_planner import generate_question_strategy

    for strategy_mode, expected in [
        ("explore", "EXPLORER"),
        ("deepen", "PROBER"),
        ("verify", "VERIFIER"),
        ("challenge", "CHALLENGER"),
        ("contradict", "VERIFIER"),
        ("validate", "CLOSER"),
        ("conclude", "CLOSER"),
    ]:
        state = make_v4_state(
            question_strategy={
                "question_strategy": {"mode": strategy_mode, "note": ""},
                "planned_competency": "tech_core",
            },
            director={"probe_mode": "deep_probe"},
        )
        assert (
            _resolve_interview_mode(state) == expected
        ), f"strategy mode {strategy_mode} should map to {expected}"


def test_resolve_interview_mode_prefers_strategy_over_director():
    state = make_v4_state(
        question_strategy={"question_strategy": {"mode": "challenge", "note": ""}},
        director={"probe_mode": "deep_probe"},
    )
    assert _resolve_interview_mode(state) == "CHALLENGER"


def test_strategy_guidance_builds_intent_line():
    from app.agents.generation.question_generator import _strategy_guidance

    state = make_v4_state(
        question_strategy={
            "question_strategy": {
                "mode": "challenge",
                "note": "pressure-test claimed seniority",
                "target_competency": "tech_system_design",
                "uncertainty": 0.61,
            },
            "rationale": "claimed seniority must be proven under pressure",
        }
    )
    guidance = _strategy_guidance(state)
    assert "challenge" in guidance
    assert "tech_system_design" in guidance
    assert "0.61" in guidance
    assert _strategy_guidance(make_v4_state()) == ""


def test_resolve_interview_mode_fallback_by_difficulty():
    assert _resolve_interview_mode(make_v4_state(difficulty_level=4)) == "CHALLENGER"
    assert _resolve_interview_mode(make_v4_state(difficulty_level=1)) == "EXPLORER"


def test_claim_targets_extracts_quantified_results():
    claims = _claim_targets(
        "We moved to a CDN and reduced load time by 30%. "
        "Error rates dropped too, and we cut costs 9x with batching."
    )
    assert any("30%" in c for c in claims)
    assert any("9x" in c for c in claims)
    assert len(claims) <= 3


def test_claim_targets_empty_without_quantification():
    assert _claim_targets("I enjoy working with React and writing clean code.") == []
    assert _claim_targets("") == []


def test_claim_targets_skips_questions_and_dedups():
    claims = _claim_targets("Did we reduce it? We reduced it. We reduced it.")
    assert len(claims) == 1


def test_resolve_interview_mode_claim_override_requires_followup():
    state = make_v4_state(director={"probe_mode": "challenge_candidate"})
    assert _resolve_interview_mode(state, claims=["30% reduction"], followup_number=0) == "CHALLENGER"
    assert _resolve_interview_mode(state, claims=["30% reduction"], followup_number=1) == "VERIFIER"
    assert (
        _resolve_interview_mode(make_v4_state(director={"probe_mode": "deep_probe"}), claims=["9x"], followup_number=2)
        == "VERIFIER"
    )
    assert _resolve_interview_mode(state, followup_number=2) == "CHALLENGER"


def test_verifier_flavor_grounds_question_in_claim():
    flavored = _apply_mode_flavor("Describe your caching solution.", "VERIFIER", "tech_core", ["reduced load time by 30%"])
    assert "30%" in flavored
    assert "measured" in flavored
    generic = _apply_mode_flavor("Describe your caching solution.", "VERIFIER", "tech_core")
    assert "measured" in generic


async def test_node_forces_verifier_and_grounds_claim_in_prompt(stub_llm):
    stub = stub_llm(response="Walk me through the data behind that 30% claim.")
    state = await question_generator_node(make_v4_state(
        director={"probe_mode": "deep_probe"},
        hypothesis_target={
            "id": "h1",
            "competency": "problem_solving",
            "statement": "Candidate has problem_solving skills",
            "status": "confirmed",
            "confidence": 0.8,
        },
        question_number=1,
        questions_asked=[{
            "id": "q0",
            "text": "Tell me about a tough production problem.",
            "competency": "problem_solving",
            "mode": "PROBER",
        }],
        conversation_history=[
            {"role": "assistant", "content": "Tell me about a tough production problem."},
            {"role": "user", "content": "I reduced queue latency by 30% and cut costs 9x using batching."},
        ],
    ))
    assert state["interview_mode"] == "VERIFIER"
    assert state["question_objective"]["mode"] == "VERIFIER"
    assert "30%" in stub.calls[0]["prompt"]
    assert "9x" in stub.calls[0]["prompt"]


async def test_node_claim_verifier_survives_llm_failure(stub_llm):
    stub_llm(fail=True)
    state = await question_generator_node(make_v4_state(
        director={"probe_mode": "deep_probe"},
        hypothesis_target={
            "id": "h1",
            "competency": "problem_solving",
            "statement": "Candidate has strong problem_solving skills",
            "status": "confirmed",
            "confidence": 0.8,
        },
        question_number=1,
        questions_asked=[{
            "id": "q0",
            "text": "Tell me about a tough production problem.",
            "competency": "problem_solving",
            "mode": "PROBER",
        }],
        conversation_history=[
            {"role": "assistant", "content": "Tell me about a tough production problem."},
            {"role": "user", "content": "I reduced queue latency by 30% with batching."},
        ],
    ))
    assert state["question_objective"]["mode"] == "VERIFIER"
    assert "30%" in state["current_question"]
    assert "measured" in state["current_question"]


async def test_node_writes_mode_into_question_objective(stub_llm):
    stub = stub_llm(response="What is your scaling strategy?")
    state = await question_generator_node(make_v4_state(
        director={"probe_mode": "deep_probe"},
        question_number=2,
    ))
    assert state["interview_mode"] == "PROBER"
    assert state["question_objective"]["type"] == "deep_probe"
    assert state["question_objective"]["mode"] == "PROBER"
    assert state["questions_asked"][-1]["mode"] == "PROBER"
    assert "PROBER" in stub.calls[0]["prompt"]


async def test_node_rejects_duplicate_and_retries(stub_llm):
    stub = stub_llm(response="How do you scale your system for production volume?")
    first = await question_generator_node(make_v4_state(question_number=0))
    state = await question_generator_node(make_v4_state(
        question_number=1,
        questions_asked=first["questions_asked"],
    ))
    assert state["questions_asked"][-1]["text"] != first["questions_asked"][0]["text"]
    assert len(stub.calls) >= 2


async def test_node_exhausts_retries_then_uses_deterministic_fallback(stub_llm):
    stub = stub_llm(responses=["How do you scale your system for production volume?"] * 2)
    first = await question_generator_node(make_v4_state(question_number=0))
    state = await question_generator_node(make_v4_state(
        question_number=1,
        questions_asked=first["questions_asked"],
    ))
    final_text = state["questions_asked"][-1]["text"]
    assert final_text != first["questions_asked"][0]["text"]
    assert final_text.strip()
    assert len(stub.calls) == 3


async def test_node_deterministic_fallback_respects_challenger_mode(stub_llm):
    stub_llm(fail=True)
    state = await question_generator_node(make_v4_state(
        difficulty_level=5,
        director={"probe_mode": "challenge_candidate"},
        question_number=0,
    ))
    assert "trade-offs" in state["current_question"]
    assert state["question_objective"]["mode"] == "CHALLENGER"
