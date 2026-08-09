"""Difficulty governor (D1): adapts difficulty from a recent-answers window —
reacts to sustained performance, never to a single noisy answer."""
from app.agents.planning.difficulty_engine import (
    _govern_deterministic,
    difficulty_governor,
    role_difficulty_floor,
)
from app.config.interview_styles import get_style
from tests.conftest import make_v4_state


def test_role_difficulty_floor_by_seniority():
    assert role_difficulty_floor("Software Engineer") == 1
    assert role_difficulty_floor("Senior Backend Engineer") == 3
    assert role_difficulty_floor("Staff Frontend Engineer") == 4
    assert role_difficulty_floor("Principal Architect") == 4
    assert role_difficulty_floor("Mid-level Backend") == 2
    assert role_difficulty_floor("Junior Developer") == 1


async def test_governor_never_below_senior_floor(monkeypatch):
    """V5: a Senior session pinned at difficulty 1 must be lifted to the 3
    floor on the next governor pass — the death-spiral guard."""

    class FailLLM:
        async def invoke(self, prompt, **kwargs):
            raise Exception("LLM down")

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: FailLLM())
    state = _state_with_evidence([7.0, 7.2], job_role="Senior Backend Engineer")
    state["difficulty_level"] = 1
    result = await difficulty_governor(state)
    assert result["difficulty_level"] == 3
    assert result["difficulty_profile"]["level"] == 3


def _state_with_evidence(scores: list, **overrides) -> dict:
    return make_v4_state(
        interview_style=get_style(),
        evidence_store=[
            {"id": f"e{i}", "question_number": i + 1, "score": s, "competency": "tech_core"}
            for i, s in enumerate(scores)
        ],
        hypothesis_target={"confidence": 0.8, "status": "testing"},
        **overrides,
    )


def test_sustained_strong_performance_increases_difficulty():
    state = _state_with_evidence([8.6, 8.9, 8.4])
    delta, rationale, _ = _govern_deterministic(state)
    assert delta == 1
    assert rationale


def test_sustained_weak_performance_decreases_difficulty():
    state = _state_with_evidence([5.0, 6.0, 4.5])
    delta, rationale, scaffold = _govern_deterministic(state)
    assert delta == -1
    assert "concrete example" in scaffold


def test_mixed_performance_keeps_steady():
    state = _state_with_evidence([7.2, 7.5, 7.1])
    delta, _, _ = _govern_deterministic(state)
    assert delta == 0


def test_single_weak_answer_is_buffered_by_window():
    """The demo regression: one 6.38 answer must NOT drop difficulty when the
    window average is still strong (8.50, 8.59, 6.38 -> 7.82)."""
    state = _state_with_evidence([8.50, 8.59, 6.38])
    delta, rationale, _ = _govern_deterministic(state)
    assert delta == 0
    assert "7.82" in rationale


def test_recovery_after_dip_holds_steady():
    state = _state_with_evidence([8.50, 8.59, 6.38, 7.25, 7.72])
    delta, _, _ = _govern_deterministic(state)
    assert delta == 0


def test_no_evidence_keeps_steady():
    state = make_v4_state(interview_style=get_style())
    delta, _, _ = _govern_deterministic(state)
    assert delta == 0


async def test_governor_clamps_to_style_range(monkeypatch):
    class FailLLM:
        async def invoke(self, prompt, **kwargs):
            raise Exception("LLM down")

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: FailLLM())

    state = _state_with_evidence([9.0])
    state["difficulty_level"] = 5  # already at ceiling
    result = await difficulty_governor(state)
    assert result["difficulty_level"] == 5
    assert result["difficulty_delta"] == 1  # requested harder, clamped


async def test_governor_reaches_level_five(monkeypatch):
    class FailLLM:
        async def invoke(self, prompt, **kwargs):
            raise Exception("LLM down")

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: FailLLM())

    state = _state_with_evidence([9.0, 9.2])
    state["difficulty_level"] = 4
    result = await difficulty_governor(state)
    assert result["difficulty_level"] == 5
    assert result["difficulty_profile"]["level"] == 5


async def test_governor_llm_failure_falls_back_to_deterministic(monkeypatch):
    class FailLLM:
        async def invoke(self, prompt, **kwargs):
            raise Exception("LLM down")

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: FailLLM())
    state = _state_with_evidence([3.0])
    state["difficulty_level"] = 3
    result = await difficulty_governor(state)
    assert result["difficulty_delta"] == -1
    assert result["difficulty_level"] == 2


async def test_governor_llm_minus_one_clamped_up_on_strong_window(stub_llm):
    """D1: the LLM may want -1, but a window average above 8.3 means sustained
    strong answers — difficulty can never drop below the deterministic rule."""
    stub_llm(response='{"delta": -1, "rationale": "complexity medium", "scaffold": ""}')
    state = _state_with_evidence([8.6, 8.9])
    state["difficulty_level"] = 2
    result = await difficulty_governor(state)
    assert result["difficulty_delta"] == 1
    assert result["difficulty_level"] == 3


async def test_governor_llm_minus_one_clamped_to_zero_on_hold_band(stub_llm):
    """Fix 11: at/above the hold band (7.0), the LLM can never lower difficulty."""
    stub_llm(response='{"delta": -1, "rationale": "complexity medium", "scaffold": ""}')
    state = _state_with_evidence([7.5, 8.0])
    state["difficulty_level"] = 2
    result = await difficulty_governor(state)
    assert result["difficulty_delta"] == 0
    assert result["difficulty_level"] == 2


async def test_governor_llm_plus_one_allowed_on_weak_window_only_via_floor(stub_llm):
    stub_llm(response='{"delta": 1, "rationale": "pushing", "scaffold": ""}')
    state = _state_with_evidence([4.0, 4.5])
    state["difficulty_level"] = 2
    result = await difficulty_governor(state)
    assert result["difficulty_delta"] == -1
    assert result["difficulty_level"] == 1


async def test_governor_llm_prompt_carries_recent_average(stub_llm):
    stub = stub_llm(response='{"delta": 0, "rationale": "steady", "scaffold": ""}')
    state = _state_with_evidence([7.1, 7.3, 7.2])
    state["difficulty_level"] = 2
    await difficulty_governor(state, use_llm=True)
    assert "7.20" in stub.calls[0]["prompt"]


def test_max_difficulty_reached_falls_back_to_current_level():
    from app.agents.planning.difficulty_engine import max_difficulty_reached

    assert max_difficulty_reached({"difficulty_level": 3}) == 3
    assert max_difficulty_reached({"max_difficulty_reached": 5, "difficulty_level": 3}) == 5
    assert max_difficulty_reached({"difficulty_level": "nonsense"}) == 1


async def test_governor_tracks_peak_difficulty_monotonically(monkeypatch):
    """B3 regression: difficulty_reached must report the peak, not the closing
    level. After hitting level 5, a governor pass that lowers back to 3 must
    keep ``max_difficulty_reached == 5``."""

    class FailLLM:
        async def invoke(self, prompt, **kwargs):
            raise Exception("LLM down")

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: FailLLM())

    state = _state_with_evidence([8.5, 8.8], job_role="Senior Backend Engineer")
    state["difficulty_level"] = 5
    state["max_difficulty_reached"] = 5
    raised = await difficulty_governor(state)
    assert raised["max_difficulty_reached"] == 5

    # Now a weak window would normally lower difficulty — the peak must stay.
    weak = _state_with_evidence([4.0, 4.5], job_role="Senior Backend Engineer")
    weak["difficulty_level"] = raised["difficulty_level"]
    weak["max_difficulty_reached"] = raised["max_difficulty_reached"]
    lowered = await difficulty_governor(weak)
    assert lowered["difficulty_level"] < raised["difficulty_level"]
    assert lowered["max_difficulty_reached"] == 5
