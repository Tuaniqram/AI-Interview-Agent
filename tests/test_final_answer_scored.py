"""Plan step 1 (P3): the answer to the last question is evaluated and becomes evidence.

The engine used to finalize as soon as an answer arrived with ``question_number >= max_questions``,
before evaluating it, so the final answer of every interview was silently dropped.
"""
import json

import pytest

from app.engine.engine import InterviewEngine
from app.services.v4_session_store import MemoryV4SessionStore
from tests.conftest import CONDUCTOR_TURN_JSON, EVALUATOR_JSON, GOVERNOR_JSON, STRATEGY_JSON, make_v4_state


class RoutingStubLLM:
    """Answers by prompt type, so a whole interview runs regardless of call order."""

    def __init__(self):
        self.calls = []

    async def invoke(self, prompt, **kwargs):
        self.calls.append(prompt)
        if "Unified Interview Evaluator" in prompt:
            return json.dumps(EVALUATOR_JSON) if isinstance(EVALUATOR_JSON, dict) else EVALUATOR_JSON
        if "Difficulty Governor" in prompt:
            return GOVERNOR_JSON
        if "Interview Question Conductor" in prompt:
            return CONDUCTOR_TURN_JSON
        if "Interview Synthesis" in prompt:
            return json.dumps({
                "holistic_score": 0, "narrative": "n", "key_strengths": [], "key_weaknesses": [],
                "fit_assessment": "Potential Fit", "interview_notes": "",
            })
        if "Evidence Reading" in prompt:
            return json.dumps({"per_answer": [], "off_rubric": {"red_flags": [], "hidden_strengths": []},
                               "semantic_risks": []})
        if "Hiring Decision" in prompt:
            return json.dumps({"rationale": "r", "next_steps": []})
        return STRATEGY_JSON


@pytest.fixture
def routing_llm(monkeypatch):
    stub = RoutingStubLLM()
    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: stub)
    return stub


@pytest.fixture
def store(tmp_path):
    return MemoryV4SessionStore(db_path=str(tmp_path / "sessions.json"))


async def _run_interview(engine, session_id, answers):
    response = None
    for answer in answers:
        response = await engine.process_answer(session_id, answer)
        if response.get("interview_complete"):
            break
    return response


async def test_last_answer_is_evaluated_and_stored_as_evidence(routing_llm, store, fake_evidence_repo, fake_repos):
    engine = InterviewEngine(store=store)
    session_id = "final-answer-scored"
    await engine.start_session(make_v4_state(session_id=session_id, max_questions=3))

    response = await _run_interview(engine, session_id, [
        "I designed the ledger schema and added row-level locking.",
        "We moved settlement from cron to Celery workers with retries.",
        "For the last one: I profiled the slow query and added a composite index.",
    ])

    assert response.get("interview_complete") is True
    brain = engine.get_brain(session_id)
    answered = {ev.get("question_number") for ev in brain.evidence_store}
    assert 3 in answered, f"final answer produced no evidence; evidence questions = {sorted(answered)}"
    evaluator_calls = [p for p in routing_llm.calls if "Unified Interview Evaluator" in p]
    assert len(evaluator_calls) == 3
    assert "composite index" in evaluator_calls[-1]


async def test_answer_after_the_report_returns_the_same_report_without_rescoring(
    routing_llm, store, fake_evidence_repo, fake_repos
):
    engine = InterviewEngine(store=store)
    session_id = "final-answer-late"
    await engine.start_session(make_v4_state(session_id=session_id, max_questions=2))
    report = await _run_interview(engine, session_id, ["First answer about caching.", "Second answer about queues."])
    assert report.get("interview_complete") is True
    evaluator_calls = sum("Unified Interview Evaluator" in p for p in routing_llm.calls)
    evidence_before = len(engine.get_brain(session_id).evidence_store)

    late = await engine.process_answer(session_id, "A late answer from a second tab.")

    assert late.get("interview_complete") is True
    assert late.get("hiring_decision") == report.get("hiring_decision")
    assert sum("Unified Interview Evaluator" in p for p in routing_llm.calls) == evaluator_calls
    assert len(engine.get_brain(session_id).evidence_store) == evidence_before
