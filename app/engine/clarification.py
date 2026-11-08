"""Clarification turns: a candidate who asks about the question is helped, not scored.

"Could you clarify what you mean by X?" or "Can you repeat the question?" used to be evaluated as an
answer (and scored badly), after which the interviewer moved to a different topic. A nervous or
non-native-speaker candidate should not be marked down for asking, so such a message gets a short
clarification of the SAME question: it is not evaluated, adds no evidence and does not use a question.
A candidate who keeps asking is limited (MAX_CLARIFICATIONS_PER_QUESTION) and then answers normally.
"""
import logging
import re

from app.core.interview_brain import InterviewBrain
from app.core.interview_state import brain_to_dict
from app.engine.store_io import store_checkpoint, store_set

logger = logging.getLogger(__name__)

MAX_CLARIFICATIONS_PER_QUESTION = 2
MAX_CLARIFICATION_CHARS = 300  # a long message is an attempt at an answer, not a request
MAX_CLARIFICATION_WORDS = 50

# Addressed to the interviewer. A bare "clarify" is deliberately NOT enough ("I'd clarify with the PM
# first" is an answer), so every pattern needs an ask: can/could you..., what do you mean..., etc.
_ASK_PATTERNS = (
    r"\b(can|could|would|will) you (please )?(just )?(repeat|rephrase|clarify|explain|elaborate|say|put|reword|restate)\b",
    r"\b(repeat|say|ask) (that|the question|it|this)( one)?( again| once more)\b",
    r"\bsay that again\b",
    r"\bcome again\b",
    r"\bwhat (do|does|did) (you|that|this|the question) mean\b",
    r"\bwhat (exactly )?are you (asking|looking for|expecting)\b",
    r"\bwhat exactly (do|does) .{0,40}\bmean\b",
    r"\b(didn'?t|did not|don'?t|do not|couldn'?t|could not) (quite )?(catch|understand|get|follow) (that|the question|what you|your question|it)\b",
    r"\bnot sure (i|what) (understand|you('re| are) asking)\b",
    r"\bi('m| am)? ?(not sure|unsure) what you('re| are) asking\b",
    r"\b(could|can) you (please )?(clarify|rephrase)\b",
    r"\bplease (repeat|rephrase|clarify)\b",
    # Plan step 9 (P9): a partial answer that asks what the interviewer wants to hear.
    r"\bremind me\b",
    r"\bwhat (do |would )?you('d| would)? (like|want) (me )?to (hear|cover|focus on|know|see)\b",
    r"\bwhat are you looking for\b",
    r"\bis that what you (meant|wanted|were asking|were looking for)\b",
)
_ASK_RE = re.compile("|".join(f"(?:{p})" for p in _ASK_PATTERNS), re.IGNORECASE)


# Plan step 9 (user decision "clarify, then let them answer"): a short partial answer that ENDS by asking the
# interviewer what they want ("...Could you remind me what you'd like to hear?") is a request, not an answer.
MAX_PARTIAL_ANSWER_WORDS = 80   # the whole message
MAX_WORDS_BEFORE_QUESTION = 40  # the partial answer before the closing question
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def is_clarification_request(answer: str) -> bool:
    """True when a message asks the interviewer to repeat or clarify the question.

    Either a short message with an ask anywhere in it, or a short partial answer whose LAST sentence is an
    ask ending in "?". A long answer that ends with a courtesy question ("does that make sense?") stays an
    answer, and so does a statement about clarifying with someone else ("I'd clarify with the PM first.").
    """
    text = (answer or "").strip().replace("’", "'")
    if not text:
        return False
    words = len(text.split())
    if len(text) <= MAX_CLARIFICATION_CHARS and words <= MAX_CLARIFICATION_WORDS and _ASK_RE.search(text):
        return True
    if words > MAX_PARTIAL_ANSWER_WORDS or not text.endswith("?"):
        return False
    sentences = [x for x in _SENTENCE_SPLIT.split(text) if x.strip()]
    last = sentences[-1] if sentences else text
    before = text[: len(text) - len(last)]
    return bool(_ASK_RE.search(last)) and len(before.split()) <= MAX_WORDS_BEFORE_QUESTION


def _fallback_reply(question: str, message: str) -> str:
    lowered = (message or "").lower()
    if "repeat" in lowered or "again" in lowered or "catch" in lowered:
        return f"Of course, here is the question again: {question}"
    return f"Happy to help. Let me put it another way: {question} Share whatever level of detail feels natural."


async def _write_reply(question: str, message: str) -> str:
    """The clarification text: the cheap model with the clarification prompt, else a plain restatement."""
    try:
        from app.services.llm_service import get_llm_service
        from app.services.prompt_loader import load_prompt

        prompt = load_prompt("interview", "clarification.md", question=question, candidate_message=message)
        reply = await get_llm_service().invoke(
            prompt=prompt, temperature=0.3, max_tokens=250, tier="cheap", attempts=2  # plan step 10
        )
        reply = (reply or "").strip().strip('"').strip()
        if reply:
            return reply[:900]
    except Exception as exc:  # noqa: BLE001 - never leave the candidate without a reply
        logger.warning(f"Clarification reply failed ({type(exc).__name__}); restating the question")
    return _fallback_reply(question, message)


def clarifications_used(brain: InterviewBrain) -> int:
    return int((getattr(brain, "clarification_counts", None) or {}).get(str(brain.question_number), 0))


def should_clarify(brain: InterviewBrain, answer: str) -> bool:
    return (
        bool(brain.current_question)
        and is_clarification_request(answer)
        and clarifications_used(brain) < MAX_CLARIFICATIONS_PER_QUESTION
    )


async def clarification_turn(engine, brain: InterviewBrain, session_id: str, answer: str) -> dict:
    """Reply to a clarification request about the current question; nothing is scored or counted."""
    from app.engine.builders import build_answer_response

    reply = await _write_reply(brain.current_question, answer)

    counts = dict(getattr(brain, "clarification_counts", None) or {})
    key = str(brain.question_number)
    counts[key] = int(counts.get(key, 0)) + 1
    brain.clarification_counts = counts
    brain.bump_version()
    store = engine._get_store()
    await store_set(store, session_id, brain.to_dict())  # the live state, then the durable checkpoint
    await store_checkpoint(store, session_id, brain.to_dict())
    await engine._get_events().append(session_id, "clarification_requested", {
        "question_number": brain.question_number,
        "length": len(answer),
        "count": counts[key],
    })

    response = build_answer_response(session_id, brain_to_dict(brain))
    response["clarification"] = True
    response["conversation_turn"] = reply
    # nothing was evaluated: do not echo the previous answer's scores as if they belonged to this turn
    response["evaluation"] = {"scores": {}, "composite": None, "scored": False}
    response["next_question"] = {
        "text": brain.current_question,
        "number": brain.question_number,
        "target_competency": (response.get("next_question") or {}).get("target_competency", ""),
    }
    return response
