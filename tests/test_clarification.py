"""A candidate who asks about the question is helped, not scored."""
import json

import pytest

from app.engine.clarification import MAX_CLARIFICATIONS_PER_QUESTION, is_clarification_request
from app.engine.engine import InterviewEngine
from app.services.v4_session_store import MemoryV4SessionStore
from tests.conftest import CONDUCTOR_TURN_JSON, EVALUATOR_JSON, GOVERNOR_JSON, STRATEGY_JSON, make_v4_state


@pytest.mark.parametrize("message", [
    "Could you repeat the question?",
    "Can you clarify what you mean by PostgreSQL-focused benchmarks? I'm a bit unsure",
    "Sorry, I didn't catch that. Can you say that again?",
    "What do you mean by idempotent here?",
    "I don’t understand the question, could you rephrase it?",
    "What exactly are you asking?",
    "Would you mind rephrasing that?".replace("Would you mind rephrasing", "Could you please rephrase"),
    "Come again?",
])
def test_requests_for_help_with_the_question_are_recognised(message):
    assert is_clarification_request(message)


@pytest.mark.parametrize("message", [
    "",
    "I would clarify the requirements with the product manager first, then design the schema.",
    "I used Redis for caching and PostgreSQL for the ledger, with idempotent Celery jobs.",
    "I don't know.",
    "To repeat what I said earlier, we used a queue.",
    # a long message that happens to contain a request is an attempt at an answer
    "Could you clarify? " + "I built the ledger service with FastAPI and PostgreSQL and moved settlement to Celery. " * 6,
])
def test_real_answers_are_not_mistaken_for_clarification_requests(message):
    assert not is_clarification_request(message)


@pytest.fixture
def engine(tmp_path):
    return InterviewEngine(store=MemoryV4SessionStore(db_path=str(tmp_path / "sessions.json")))


async def _started(engine, stub_llm, *later):
    stub = stub_llm(responses=[STRATEGY_JSON, "Question: How would you design the ledger?", *later])
    await engine.start_session(make_v4_state(session_id="clar-1", flow_type="v5_evidence_driven"))
    return stub


async def test_a_clarification_gets_a_reply_to_the_same_question_and_is_not_scored(
    engine, stub_llm, fake_evidence_repo, fake_repos
):
    stub = await _started(engine, stub_llm, "Sure - I mean how you would structure the ledger service.")
    calls_before = len(stub.calls)
    before = engine.get_brain("clar-1")

    reply = await engine.process_answer("clar-1", "Could you clarify what you mean by structure?")

    assert reply["clarification"] is True and reply["status"] == "in_progress"
    assert reply["conversation_turn"].startswith("Sure - I mean how you would structure")
    assert reply["next_question"]["text"] == before.current_question
    assert reply["next_question"]["number"] == before.question_number
    assert reply["evaluation"] == {"scores": {}, "composite": None, "scored": False}
    assert len(stub.calls) - calls_before == 1  # one cheap clarification call: no evaluation, no governor

    after = engine.get_brain("clar-1")
    assert after.question_number == before.question_number
    assert after.evidence_store == [] and after.current_question == before.current_question
    assert after.clarification_counts == {str(before.question_number): 1}
    assert not any(h.get("content") == "Could you clarify what you mean by structure?" for h in after.conversation_history)


async def test_a_failing_model_still_restates_the_question(engine, stub_llm, fake_evidence_repo, fake_repos):
    stub = await _started(engine, stub_llm)
    stub.fail = True
    reply = await engine.process_answer("clar-1", "Can you repeat the question?")
    assert reply["clarification"] is True
    assert "How would you design the ledger?" in reply["conversation_turn"]


async def test_clarifications_are_limited_then_the_message_is_treated_as_an_answer(
    engine, stub_llm, fake_evidence_repo, fake_repos
):
    later = [f"Clarification {i}." for i in range(MAX_CLARIFICATIONS_PER_QUESTION)]
    await _started(engine, stub_llm, *later, json.dumps(EVALUATOR_JSON), GOVERNOR_JSON, CONDUCTOR_TURN_JSON)

    for _ in range(MAX_CLARIFICATIONS_PER_QUESTION):
        assert (await engine.process_answer("clar-1", "Could you repeat the question?"))["clarification"] is True

    third = await engine.process_answer("clar-1", "Could you repeat the question?")
    assert "clarification" not in third  # now it is evaluated like any answer
    assert third["next_question"]["text"]


async def test_a_real_answer_after_a_clarification_is_scored_normally(engine, stub_llm, fake_evidence_repo, fake_repos):
    await _started(engine, stub_llm, "Here is another way to put it.", json.dumps(EVALUATOR_JSON), GOVERNOR_JSON, CONDUCTOR_TURN_JSON)
    await engine.process_answer("clar-1", "Could you rephrase that?")
    reply = await engine.process_answer("clar-1", "I would start with an append-only ledger table in PostgreSQL.")
    assert "clarification" not in reply
    assert reply["evaluation"]["scored"] is True


# --- plan step 9: a short partial answer that ends by asking what the interviewer wants --------------------

from app.engine.clarification import is_clarification_request as _is_clar  # noqa: E402

ROUND8_AWKWARD_TURN7 = (
    "I'm not sure I remember if we added a cache at all... Maybe we cached some lookup tables in Redis, but I "
    "can't recall the invalidation strategy. Could you remind me what you'd like to hear?"
)


def test_round8_awkward_turn7_is_a_clarification():
    assert _is_clar(ROUND8_AWKWARD_TURN7)
    assert _is_clar(ROUND8_AWKWARD_TURN7.replace("'", "’"))  # curly apostrophes


def test_new_phrasings_are_clarifications():
    for text in (
        "What are you looking for here?",
        "Sorry, what would you like me to focus on?",
        "We used Postgres for it. Is that what you meant?",
        "Could you remind me of the question?",
    ):
        assert _is_clar(text), text


def test_long_answer_ending_with_a_courtesy_question_stays_an_answer():
    body = " ".join(["We split the ledger into services and added row level locking on the balance table."] * 8)
    text = body + " Does that make sense?"
    assert len(text.split()) > 100
    assert not _is_clar(text)
    # a long partial answer before the closing ask is still an answer
    long_lead = " ".join(["I worked on the cache layer and measured the hit rate each week."] * 4)
    assert not _is_clar(long_lead + " What are you looking for?")


def test_statements_about_clarifying_are_answers():
    assert not _is_clar("I'd clarify with the PM first.")
    assert not _is_clar("I would ask the team to clarify the requirements before building anything.")
