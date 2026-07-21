"""
Shared fixtures for backend tests.
Disposes the async engine after each test that used it, to avoid event-loop
isolation issues (pytest-asyncio creates a new event loop per function, but
the async engine's connection pool retains connections bound to the previous
loop).  Only disposes if a test actually created the engine — tests that don't
touch the DB pay no overhead.
"""
import logging
from unittest.mock import AsyncMock

import pytest

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Yield, then dispose the engine (if the test created one) while still in
    this test's event loop, so the next test starts with a fresh pool."""
    yield
    from app.database.session import _engine
    eng = _engine  # read module-level ref without triggering lazy creation
    if eng is not None:
        try:
            await eng.dispose()
        except RuntimeError:
            # Some tests (e.g. test_full_interview.py) use their own event loop
            # via _run(), leaving the engine's connections bound to a closed
            # loop.  Forcefully null the reference so the next test creates a
            # fresh engine in the correct loop.
            pass
        finally:
            # Force recreation on next use regardless
            from app.database.session import _engine as e
            if e is eng:
                import app.database.session as mod
                mod._engine = None
                mod._async_session_factory = None


# ---------------------------------------------------------------------------
# Mock LLM — returns canned responses so tests are fast & deterministic
# ---------------------------------------------------------------------------

_MOCK_EVALUATION = (
    '```json\n'
    '{\n'
    '  "score": 7.5,\n'
    '  "technical_score": 7.0,\n'
    '  "communication_score": 8.0,\n'
    '  "strengths": ["Good technical knowledge", "Clear communication"],\n'
    '  "weaknesses": ["Could provide more detail"],\n'
    '  "feedback": "Strong answer with relevant experience.",\n'
    '  "next_action": "continue"\n'
    '}\n'
    '```'
)

_MOCK_QUESTION = (
    "Tell me about a complex backend system you designed. "
    "What were the key architectural decisions and trade-offs?"
)


class _MockResponse:
    """Mimics LangChain's AIMessage with .content attribute."""
    def __init__(self, content: str):
        self.content = content


import hashlib


def _canned_question(prompt_text: str) -> str:
    """Return a deterministic question based on the prompt content,
    so tests that compare questions across companies/job roles see differences.

    Uses a hash of distinctive prompt segments as the seed, so any change
    in role, company, or RAG context produces a different question."""
    # Extract distinctive tokens: role, difficulty, company context keywords
    seed_parts = []
    for kw in ["backend", "frontend", "full stack", "devops", "data",
               "engineer", "manager", "architect", "analyst",
               "oil", "gas", "drilling", "it", "software", "finance",
               "healthcare", "retail", "banking", "insurance", "manufacturing",
               "company", "difficulty", "phase"]:
        if kw in prompt_text:
            # Find the sentence/context around it
            idx = prompt_text.find(kw)
            ctx = prompt_text[max(0,idx-30):idx+len(kw)+30]
            seed_parts.append(ctx)

    if not seed_parts:
        # Fallback: hash the whole thing
        seed_parts = [prompt_text[:200]]

    seed = "|".join(seed_parts)
    h = hashlib.md5(seed.encode()).hexdigest()[:8]
    # Use hash as numeric seed to pseudo-randomly pick from a question bank
    num = int(h, 16)
    bank = [
        "Tell me about a project you're proud of.",
        "What's the most challenging bug you've fixed?",
        "How do you approach learning a new technology?",
        "Describe a time you had to make a difficult technical decision.",
        "What does good code mean to you?",
        "Tell me about a time you disagreed with a team member.",
        "How do you stay current with industry trends?",
        "Describe your ideal development workflow.",
    ]
    return bank[num % len(bank)]


async def _mock_ainvoke(self, messages, config=None, **kwargs):
    """Patched FallbackLLM.ainvoke that returns a context-aware canned response."""
    # Flatten all message content for prompt inspection
    prompt_text = " ".join(
        m.get("content", "") if isinstance(m, dict) else str(m)
        for m in (messages or [])
    ).lower()

    # Prioritise: question generation first (prompts ask to generate a question)
    if "generate" in prompt_text and "question" in prompt_text:
        return _MockResponse(_canned_question(prompt_text))
    # Evaluation prompts mention scoring
    if "score" in prompt_text or "evaluat" in prompt_text or "scoring" in prompt_text:
        return _MockResponse(_MOCK_EVALUATION)
    # Default: short generic answer
    return _MockResponse("This is a mock LLM response for testing purposes.")


async def _mock_astream(self, messages, config=None, **kwargs):
    """Patched FallbackLLM.astream that yields the canned response token by token."""
    prompt_text = " ".join(
        m.get("content", "") if isinstance(m, dict) else str(m)
        for m in (messages or [])
    ).lower()

    if "generate" in prompt_text and "question" in prompt_text:
        for token in _canned_question(prompt_text).split():
            yield token
    elif "score" in prompt_text or "evaluat" in prompt_text or "scoring" in prompt_text:
        for token in _MOCK_EVALUATION.split():
            yield token
    else:
        yield "mock response"


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    """Replace real FallbackLLM with a mock that returns canned responses.
    This is autouse for ALL backend tests — overridable per test if needed.
    """
    # Patch FallbackLLM.ainvoke — patch the unbound method on the class
    monkeypatch.setattr(
        "app.models.llm.FallbackLLM.ainvoke",
        _mock_ainvoke,
    )
    monkeypatch.setattr(
        "app.models.llm.FallbackLLM.astream",
        _mock_astream,
    )
    logger.info("Mock LLM patched — all LLM calls return canned responses")
