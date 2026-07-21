"""
Company Comparison Test - Verifies AI generates different questions
for different companies based on their RAG context.

Usage:
  cd D:\projectiqram\AI\AI-Interview-Agent
  .\venv\Scripts\python -m pytest tests/backend/test_company_comparison.py -v -s

Requires:
  - .env with Pinecone + OpenRouter credentials
  - Different RAG documents uploaded for company_id=1 and company_id=2
"""
import asyncio
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("company_comparison")


def _run(coro):
    """Run async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


_LLM_AVAILABLE = None

def _is_llm_available():
    global _LLM_AVAILABLE
    if _LLM_AVAILABLE is not None:
        return _LLM_AVAILABLE
    try:
        from app.services.llm_service import get_llm_service
        svc = get_llm_service()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(svc.invoke(
                prompt="Say OK", temperature=0.1, max_tokens=5
            ))
            _LLM_AVAILABLE = bool(result and len(result.strip()) > 0)
        finally:
            loop.close()
    except Exception as e:
        logger.warning(f"LLM probe failed: {e}")
        _LLM_AVAILABLE = False
    if not _LLM_AVAILABLE:
        logger.warning("LLM not available — company comparison tests SKIPPED")
    return _LLM_AVAILABLE


requires_llm = pytest.mark.skipif(
    not _is_llm_available(),
    reason="LLM not available (no credits / local model down)"
)


def _get_rag_context(company_id: int, job_role: str) -> str:
    """Query Pinecone for a company's RAG context."""
    try:
        from app.rag.pinecone_store import get_company_retriever
        retriever = get_company_retriever(company_id)
        query = f"Company interview requirements. Role: {job_role}. Generate suitable interview questions."
        docs = retriever.invoke(query)
        context = "\n".join([doc.page_content for doc in docs])
        logger.info(f"Company {company_id} RAG: {len(context)} chars, {len(docs)} docs")
        return context
    except Exception as e:
        logger.warning(f"Company {company_id} RAG failed: {e}")
        return ""


def _generate_question(company_id: int, job_role: str, company_requirements: str) -> str:
    """Generate a single intro question for a company using real AI."""
    from app.agents.question_generation_node import question_generation_node

    state = {
        "session_id": f"test-company-{company_id}",
        "job_role": job_role,
        "current_phase": "intro",
        "difficulty_level": 1,
        "conversation_history": [],
        "company_requirements": company_requirements,
        "candidate_profile": "{}",
        "question_number": 0,
        "total_questions": 10,
        "rag_metadata": {},
        "nodes_executed": [],
    }
    result = _run(question_generation_node(state))
    question = result.get("current_question", "")
    logger.info(f"Company {company_id} ({job_role}) Q1: {question}")
    return question


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@requires_llm
class TestCompanyComparison:
    """Verify AI generates different questions for different companies."""

    def test_intro_questions_differ_by_company(self):
        """
        Generate intro Q1 for company_id=1 and company_id=2.
        Assert the questions are different strings.
        """
        # 1. Get RAG context for each company
        ctx_1 = _get_rag_context(company_id=1, job_role="Backend Developer")
        ctx_2 = _get_rag_context(company_id=2, job_role="Backend Developer")

        logger.info(f"Company 1 RAG preview: {ctx_1[:200]}")
        logger.info(f"Company 2 RAG preview: {ctx_2[:200]}")

        # 2. Generate intro questions
        q1 = _generate_question(
            company_id=1,
            job_role="Backend Developer",
            company_requirements=ctx_1
        )
        q2 = _generate_question(
            company_id=2,
            job_role="Backend Developer",
            company_requirements=ctx_2
        )

        # 3. Assert both questions are non-empty
        assert q1, "Company 1 question is empty"
        assert q2, "Company 2 question is empty"
        assert len(q1) > 10, f"Company 1 question too short: {q1}"
        assert len(q2) > 10, f"Company 2 question too short: {q2}"

        # 4. Assert questions are different
        assert q1.strip() != q2.strip(), (
            f"Questions are identical! Company RAG context may be the same.\n"
            f"Company 1: {q1}\n"
            f"Company 2: {q2}"
        )

        # 5. Log results for manual review
        logger.info("=" * 60)
        logger.info("COMPARISON RESULT:")
        logger.info(f"  Company 1 Q1: {q1}")
        logger.info(f"  Company 2 Q1: {q2}")
        logger.info(f"  Questions differ: YES")
        logger.info("=" * 60)

    def test_intro_questions_differ_by_job_role(self):
        """
        Same company (id=1), different job roles.
        Assert the questions are different.
        """
        ctx = _get_rag_context(company_id=1, job_role="any role")

        q_drilling = _generate_question(
            company_id=1,
            job_role="Drilling Engineer",
            company_requirements=ctx
        )
        q_backend = _generate_question(
            company_id=1,
            job_role="Backend Developer",
            company_requirements=ctx
        )

        assert q_drilling, "Drilling Engineer question is empty"
        assert q_backend, "Backend Developer question is empty"

        assert q_drilling.strip() != q_backend.strip(), (
            f"Questions are identical despite different job roles!\n"
            f"Drilling: {q_drilling}\n"
            f"Backend: {q_backend}"
        )

        logger.info("=" * 60)
        logger.info("JOB ROLE COMPARISON:")
        logger.info(f"  Drilling Engineer: {q_drilling}")
        logger.info(f"  Backend Developer: {q_backend}")
        logger.info(f"  Questions differ: YES")
        logger.info("=" * 60)

    def test_different_rag_context_produces_different_questions(self):
        """
        Same job role, manually different RAG context strings.
        Proves the prompt system injects company context correctly.
        """
        ctx_oil = """
        Oil & Gas company requirements:
        - Drilling operations safety protocols
        - Well completion and workover procedures
        - Production optimization
        - HSE compliance and risk management
        - Upstream operations experience required
        """

        ctx_it = """
        IT company requirements:
        - Backend development with Python/FastAPI
        - Database design and optimization
        - Cloud infrastructure (AWS/GCP)
        - CI/CD pipelines and DevOps
        - Microservices architecture
        """

        q_oil = _generate_question(
            company_id=999,
            job_role="Operations Engineer",
            company_requirements=ctx_oil
        )
        q_it = _generate_question(
            company_id=999,
            job_role="Operations Engineer",
            company_requirements=ctx_it
        )

        assert q_oil, "Oil & Gas question is empty"
        assert q_it, "IT question is empty"
        assert q_oil.strip() != q_it.strip(), (
            f"Questions are identical despite different RAG context!\n"
            f"Oil & Gas: {q_oil}\n"
            f"IT: {q_it}"
        )

        logger.info("=" * 60)
        logger.info("RAG CONTEXT COMPARISON:")
        logger.info(f"  Oil & Gas: {q_oil}")
        logger.info(f"  IT: {q_it}")
        logger.info(f"  Questions differ: YES")
        logger.info("=" * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
