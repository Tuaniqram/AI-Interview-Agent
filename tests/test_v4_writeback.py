"""V5/AURA DB write-back tests against ``app.engine.persistence``.

Covers the best-effort persistence of evaluated turns and session completion:
per-turn message + evaluation rows, completion row updates (status, final_score,
ended_at, engine_version), dedupe, and fail-safe behavior.
"""
from datetime import datetime

import pytest

from app.core.interview_brain import InterviewBrain
from app.engine.persistence import (
    extract_answer_turn,
    persist_answer_turn,
    persist_completion,
)


def _turn_brain(**overrides) -> InterviewBrain:
    brain = InterviewBrain(
        session_id="session-1",
        current_question="Walk me through a distributed system you built.",
        candidate_answer="I built a payment platform that processed 1M requests/day.",
        question_number=2,
        current_phase="technical",
        evaluation_score=7.6,
        conversation_history=[
            {"role": "assistant", "content": "Walk me through a distributed system you built."},
            {"role": "user", "content": "I built a payment platform that processed 1M requests/day."},
        ],
        unified_evaluation={
            "technical": {"score": 8.0, "strengths": ["solid design"], "weaknesses": []},
            "communication": {"score": 7.0, "strengths": [], "weaknesses": ["verbose"]},
            "reasoning": {"score": 6.5, "strengths": [], "weaknesses": []},
            "behavioral": {"score": None, "strengths": [], "weaknesses": []},
            "confidence": {"score": 7.5, "strengths": [], "weaknesses": []},
            "completeness": {"score": 8.5, "strengths": [], "weaknesses": []},
        },
    )
    for k, v in overrides.items():
        setattr(brain, k, v)
    return brain


def test_extract_answer_turn():
    turn = extract_answer_turn(_turn_brain())
    assert turn["question"] == "Walk me through a distributed system you built."
    assert turn["answer"].startswith("I built a payment platform")
    assert turn["question_number"] == 2
    assert turn["phase"] == "technical"
    assert turn["composite"] == pytest.approx(7.6)


def test_extract_answer_turn_short_history():
    assert extract_answer_turn(InterviewBrain()) is None
    assert (
        extract_answer_turn(InterviewBrain(conversation_history=[{"role": "assistant", "content": "hi"}]))
        is None
    )


@pytest.mark.asyncio
async def test_persist_answer_turn_writes_rows(fake_repos):
    brain = _turn_brain()
    await persist_answer_turn("session-1", brain)

    assert len(fake_repos["messages"].questions) == 1
    assert len(fake_repos["messages"].answers) == 1
    assert len(fake_repos["evaluations"].saved) == 1

    question = fake_repos["messages"].questions[0]
    assert question["question_number"] == 2
    assert question["phase"] == "technical"

    answer = fake_repos["messages"].answers[0]
    assert answer["score"] == pytest.approx(7.6)

    evaluation = fake_repos["evaluations"].saved[0]
    assert evaluation["message_id"] == answer["id"]
    assert evaluation["overall_score"] == pytest.approx(7.6)
    assert evaluation["technical_score"] == pytest.approx(8.0)
    assert evaluation["communication_score"] == pytest.approx(7.0)
    assert "solid design" in evaluation["strengths"]
    assert "verbose" in evaluation["weaknesses"]
    assert brain.answered_question_numbers == [2]


@pytest.mark.asyncio
async def test_persist_answer_turn_dedupes_on_resend(fake_repos):
    brain = _turn_brain()
    await persist_answer_turn("session-1", brain)
    await persist_answer_turn("session-1", brain)

    assert len(fake_repos["messages"].questions) == 1
    assert len(fake_repos["evaluations"].saved) == 1


@pytest.mark.asyncio
async def test_persist_completion_writes_session_row(fake_repos):
    brain = _turn_brain(
        hiring_recommendation={
            "verdict": "hire",
            "confidence": 0.8,
            "composite_score": 7.4,
        },
        evidence_store=[{"id": "e1"}, {"id": "e2"}],
    )
    await persist_completion("session-1", brain)

    assert len(fake_repos["sessions"].completions) == 1
    completion = fake_repos["sessions"].completions[0]
    assert completion["session_id"] == "session-1"
    assert completion["final_score"] == pytest.approx(7.4)
    assert completion["engine_version"] == "v5"
    assert isinstance(completion["ended_at"], datetime)
    assert "hire" in completion["final_feedback"]


@pytest.mark.asyncio
async def test_persist_is_failsafe(monkeypatch, fake_repos):
    async def boom(*args, **kwargs):
        raise RuntimeError("db down")

    broken_messages = type("X", (), {"create_question": boom, "create_candidate_answer": boom})()
    broken_sessions = type("X", (), {"complete_session": boom})()

    monkeypatch.setattr("app.services.repositories.get_message_repo", lambda: broken_messages)
    monkeypatch.setattr("app.services.repositories.get_session_repo", lambda: broken_sessions)

    brain = _turn_brain()
    await persist_answer_turn("session-1", brain)
    await persist_completion("session-1", brain)
