"""AURA turn composer: one LLM call produces {acknowledgement, bridge, question},
the evaluable question stays in current_question."""
from app.agents.generation.question_generator import (
    _generate_deterministic_conductor_turn,
    _parse_conductor_turn,
    question_generator_node,
)
from app.config.interview_styles import get_style
from tests.conftest import CONDUCTOR_TURN_JSON, make_v4_state


def test_parse_conductor_turn():
    turn = _parse_conductor_turn(CONDUCTOR_TURN_JSON)
    assert turn == {
        "acknowledgement": "Got it.",
        "bridge": "Let me dig into that.",
        "question": "Walk me through a concrete example of that.",
    }


def test_parse_conductor_turn_strips_code_fence():
    turn = _parse_conductor_turn(f"```json\n{CONDUCTOR_TURN_JSON}\n```")
    assert turn["question"] == "Walk me through a concrete example of that."


def test_parse_conductor_turn_rejects_missing_question():
    import pytest

    with pytest.raises(ValueError):
        _parse_conductor_turn('{"acknowledgement": "ok", "bridge": "", "question": ""}')


def test_deterministic_conductor_turn_composes_message():
    turn = _generate_deterministic_conductor_turn(
        target_competency="tech_core",
        job_role="Software Engineer",
        difficulty=2,
        hypothesis_text="",
        competency_info="",
        last_answer="I built a caching layer.",
    )
    assert turn["acknowledgement"]
    assert turn["bridge"]
    assert turn["question"]
    assert "tech core" in turn["bridge"]


async def test_question_generator_sets_conversation_turn_for_conductor(monkeypatch):
    class StubLLM:
        def __init__(self):
            self.calls = []

        async def invoke(self, prompt, **kwargs):
            self.calls.append(prompt)
            return CONDUCTOR_TURN_JSON

    stub = StubLLM()
    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: stub)

    state = make_v4_state(
        persona="conductor",
        interview_style=get_style(),
        difficulty_level=2,
        hypothesis_target={"competency": "tech_core", "statement": "Strong tech_core", "id": "h1"},
        competency_summary={"tech_core": {"average_score": 7.0, "evidence_count": 2, "gap": 0.2}},
        conversation_history=[{"role": "user", "content": "I handled caching at scale."}],
        questions_asked=[],
    )

    result = await question_generator_node(state)

    assert result["current_question"] == "Walk me through a concrete example of that."
    assert result["conversation_turn"] == {
        "acknowledgement": "Got it.",
        "bridge": "Let me dig into that.",
        "question": "Walk me through a concrete example of that.",
    }
    assert result["question_objective"]["target_competency"] == "tech_core"
    assert result["questions_asked"][-1]["text"] == "Walk me through a concrete example of that."
    assert len(stub.calls) == 1  # single LLM call per turn


async def test_question_generator_conductor_llm_failure_falls_back(monkeypatch):
    class FailLLM:
        async def invoke(self, prompt, **kwargs):
            raise Exception("LLM down")

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: FailLLM())

    state = make_v4_state(
        persona="conductor",
        interview_style=get_style(),
        difficulty_level=2,
        hypothesis_target={"competency": "tech_core", "statement": "Strong tech_core", "id": "h1"},
        competency_summary={"tech_core": {"average_score": 7.0, "evidence_count": 2, "gap": 0.2}},
        conversation_history=[{"role": "user", "content": "I handled caching at scale."}],
    )

    result = await question_generator_node(state)

    turn = result["conversation_turn"]
    assert turn["acknowledgement"] == "Got it. Let me dig into that."
    assert result["current_question"]
    assert result["current_question"] == turn["question"]


async def test_question_generator_legacy_persona_keeps_old_behavior(monkeypatch):
    class StubLLM:
        async def invoke(self, prompt, **kwargs):
            return "Question: What happens at scale?"

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: StubLLM())

    state = make_v4_state(
        persona="friendly",
        interview_style=get_style(),
        difficulty_level=2,
        hypothesis_target={"competency": "tech_core", "statement": "Strong tech_core", "id": "h1"},
    )

    result = await question_generator_node(state)

    assert result["current_question"] == "What happens at scale?"
    assert result["conversation_turn"] is None
