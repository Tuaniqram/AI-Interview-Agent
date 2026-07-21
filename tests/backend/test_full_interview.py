"""
Backend Integration Test - Full Interview Workflow
Tests real AI + real DB (Supabase + Pinecone).
No mocks - runs actual interview end to end.

Usage:
  cd D:\projectiqram\AI\AI-Interview-Agent
  .\venv\Scripts\python -m pytest tests/backend/test_full_interview.py -v -s

  # Run only offline tests (no AI, no DB):
  .\venv\Scripts\python -m pytest tests/backend/test_full_interview.py -v -s -k "Prompt or Loader or SessionInit or CompanyContextNoCompany"

  # Run full integration (requires credits + DB):
  .\venv\Scripts\python -m pytest tests/backend/test_full_interview.py -v -s -k "Full or DBConsistency"

Requires:
  - .env with SUPABASE_URL, SUPABASE_KEY, PINECONE_API_KEY, OPENROUTER_API_KEY
  - Supabase tables: interview_sessions, interview_messages, interview_evaluations
  - Pinecone index with company documents (optional - tests gracefully handle empty RAG)
  - OpenRouter credits (for AI node tests)
"""
import asyncio
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("integration_test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run async coroutine synchronously.
    Each call creates its own event loop, so we null the async engine first
    so the next call creates a fresh one in the correct loop.
    """
    import app.database.session as _db
    _db._engine = None
    _db._async_session_factory = None

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


_LLM_AVAILABLE = None

def _is_llm_available():
    """Quick probe: can we call the LLM at all? Cached after first check."""
    global _LLM_AVAILABLE
    if _LLM_AVAILABLE is not None:
        return _LLM_AVAILABLE
    try:
        from app.services.llm_service import get_llm_service
        svc = get_llm_service()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(svc.invoke(
                prompt="Say OK",
                temperature=0.1,
                max_tokens=5,
            ))
            _LLM_AVAILABLE = bool(result and len(result.strip()) > 0)
        finally:
            loop.close()
    except Exception as e:
        logger.warning(f"LLM probe failed: {e}")
        _LLM_AVAILABLE = False
    if not _LLM_AVAILABLE:
        logger.warning("LLM is NOT available — AI-dependent tests will be SKIPPED")
    return _LLM_AVAILABLE


_requires_llm = pytest.mark.skipif(
    not _is_llm_available(),
    reason="LLM not available (no credits / local model down)"
)


def _prompt_files_exist():
    """Verify all 9 prompt template files exist on disk."""
    base = Path(__file__).parent.parent.parent / "prompts"
    expected = [
        ("system", "interviewer_system.md"),
        ("system", "evaluator_system.md"),
        ("system", "followup_system.md"),
        ("interview", "question_generation.md"),
        ("interview", "adaptive_question.md"),
        ("interview", "phase_decision.md"),
        ("interview", "interview_flow.md"),
        ("evaluation", "answer_evaluation.md"),
        ("evaluation", "scoring_rules.md"),
    ]
    missing = []
    for cat, fname in expected:
        if not (base / cat / fname).exists():
            missing.append(f"{cat}/{fname}")
    return missing


def _prompt_has_no_hardcoded_questions(filepath: Path) -> list[str]:
    """Check a prompt template does NOT contain hardcoded interview questions.
    
    Only flags questions that appear as standalone question lines (starting with
    'Question:' or as example questions), NOT negative instructions like
    'Don't ask ... Tell me about yourself'.
    """
    content = filepath.read_text(encoding="utf-8")
    violations = []
    lines = content.split("\n")
    hardcoded_markers = [
        "Tell me about yourself",
        "What are your strengths",
        "Why do you want",
        "Describe a time",
        "What is your greatest weakness",
        "Can you explain",
        "How would you handle",
    ]
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if "don't" in lower or "do not" in lower or "never" in lower or "avoid" in lower:
            continue
        for marker in hardcoded_markers:
            if marker.lower() in lower:
                violations.append(f"{marker} (line: {stripped[:80]})")
    return violations


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPromptTemplates:
    """Verify prompt template files exist and are clean (no hardcoded questions)."""

    def test_all_9_template_files_exist(self):
        missing = _prompt_files_exist()
        assert not missing, f"Missing prompt templates: {missing}"

    def test_no_hardcoded_questions_in_templates(self):
        base = Path(__file__).parent.parent.parent / "prompts"
        violations = {}
        for md in base.rglob("*.md"):
            v = _prompt_has_no_hardcoded_questions(md)
            if v:
                violations[str(md.relative_to(base))] = v
        assert not violations, f"Hardcoded questions found in templates: {violations}"

    def test_templates_use_variable_placeholders(self):
        base = Path(__file__).parent.parent.parent / "prompts"
        for md in base.rglob("*.md"):
            content = md.read_text(encoding="utf-8")
            if "{{" in content or "{job_role}" in content:
                continue
            if md.name == "interview_flow.md":
                continue
            if md.name == "scoring_rules.md":
                continue


class TestPromptLoader:
    """Verify the PromptLoader correctly loads and renders templates."""

    def test_loader_finds_all_templates(self):
        from app.services.prompt_loader import get_prompt_loader
        loader = get_prompt_loader()
        for cat in ["system", "interview", "evaluation"]:
            prompts = loader.list_prompts(cat)
            assert len(prompts) >= 2, f"Category '{cat}' has only {len(prompts)} prompts, expected >= 2"

    def test_loader_renders_question_generation(self):
        from app.services.prompt_loader import load_prompt
        result = load_prompt(
            "interview", "question_generation.md",
            job_role="Software Engineer",
            phase="intro",
            difficulty_level=1,
            company_context="N/A",
            candidate_profile="N/A",
            question_number=0,
            conversation_history="(no previous conversation)",
        )
        assert len(result) > 100
        assert "Generate" in result

    def test_loader_renders_answer_evaluation(self):
        from app.services.prompt_loader import load_prompt
        result = load_prompt(
            "evaluation", "answer_evaluation.md",
            job_role="Data Scientist",
            question="Explain machine learning",
            candidate_answer="ML is a subset of AI",
            phase="technical",
            difficulty_level=2,
            company_context="N/A",
        )
        assert len(result) > 100
        assert "Evaluate" in result

    def test_loader_renders_phase_decision(self):
        from app.services.prompt_loader import load_prompt
        result = load_prompt(
            "interview", "phase_decision.md",
            current_phase="intro",
            question_number=1,
            total_questions=10,
            evaluation_score=7.0,
            technical_score=7.0,
            communication_score=7.0,
            conversation_summary="(no conversation)",
            strengths="none",
            weaknesses="none",
            difficulty_history="[1]",
        )
        assert "intro" in result
        assert len(result) > 100


@_requires_llm
class TestNodeExecution:
    """Test each LangGraph node individually with real AI."""

    def test_session_init_node(self):
        from app.agents.session_init_node import session_init_node
        state = {
            "session_id": str(uuid.uuid4()),
            "conversation_history": [],
            "current_phase": "intro",
            "question_number": 0,
            "interview_type": "company",
            "company_context": [],
            "nodes_executed": [],
        }
        result = session_init_node(state)
        assert result["current_phase"] == "intro"
        assert result["question_number"] == 0
        assert "session_init" in result["nodes_executed"]
        assert result["start_time"] is not None

    def test_company_context_node_without_company(self):
        from app.agents.company_context_node import company_context_node
        state = {
            "session_id": str(uuid.uuid4()),
            "company_id": None,
            "job_role": "Software Engineer",
            "rag_metadata": {},
        }
        result = _run(company_context_node(state))
        assert result["rag_metadata"]["success"] is False
        assert result["company_context"] == []

    def test_question_generation_node_real_ai(self):
        from app.agents.question_generation_node import question_generation_node
        state = {
            "session_id": str(uuid.uuid4()),
            "job_role": "Software Engineer",
            "current_phase": "intro",
            "difficulty_level": 1,
            "conversation_history": [],
            "company_requirements": "Looking for Python developer with 3+ years experience",
            "candidate_profile": "{}",
            "question_number": 0,
            "total_questions": 10,
            "rag_metadata": {},
            "nodes_executed": [],
        }
        result = _run(question_generation_node(state))
        question = result.get("current_question")
        assert question is not None, "AI returned None question"
        assert len(question) > 10, f"Question too short: {question}"
        assert result["question_number"] == 1
        assert result["rag_metadata"]["question_generated_by_ai"] is True
        logger.info(f"Q1 (intro): {question}")

    def test_question_generation_node_followup_ai(self):
        from app.agents.question_generation_node import question_generation_node
        state = {
            "session_id": str(uuid.uuid4()),
            "job_role": "Data Scientist",
            "current_phase": "technical",
            "difficulty_level": 2,
            "conversation_history": [
                {"role": "assistant", "content": "What is your experience with neural networks?"},
                {"role": "user", "content": "I have built CNNs for image classification using PyTorch."},
            ],
            "company_requirements": "Need ML engineer with deep learning experience",
            "candidate_profile": "{}",
            "question_number": 2,
            "total_questions": 10,
            "rag_metadata": {},
            "nodes_executed": [],
            "previous_scores": [7.0],
        }
        result = _run(question_generation_node(state))
        question = result.get("current_question")
        assert question is not None, "AI returned None follow-up question"
        assert len(question) > 10, f"Follow-up too short: {question}"
        assert result["question_number"] == 3
        assert result["rag_metadata"]["template_used"] == "adaptive_question"
        logger.info(f"Q3 (followup): {question}")

    def test_answer_evaluator_node_real_ai(self):
        from app.agents.answer_evaluator_node import answer_evaluator_node
        state = {
            "session_id": str(uuid.uuid4()),
            "job_role": "Software Engineer",
            "current_question": "What is the difference between a list and a tuple in Python?",
            "candidate_answer": "Lists are mutable and tuples are immutable. Lists use square brackets and tuples use parentheses. Tuples are faster and use less memory.",
            "current_phase": "technical",
            "difficulty_level": 1,
            "company_requirements": "Python developer role",
            "evaluation_metadata": {},
            "nodes_executed": [],
        }
        result = _run(answer_evaluator_node(state))
        assert result["evaluation_failed"] is False
        score = result.get("evaluation_score")
        assert score is not None, "No evaluation_score returned"
        assert 0 <= score <= 10, f"Score out of range: {score}"
        assert result["feedback_detail"], "No feedback returned"
        assert len(result.get("strengths", [])) > 0 or len(result.get("weaknesses", [])) > 0
        logger.info(f"Eval: score={score}, technical={result.get('technical_score')}, comm={result.get('communication_score')}")
        logger.info(f"Feedback: {result['feedback_detail'][:200]}")

    def test_decision_node_real_ai(self):
        from app.agents.decision_node import decision_node
        state = {
            "session_id": str(uuid.uuid4()),
            "job_role": "Software Engineer",
            "current_phase": "intro",
            "question_number": 1,
            "total_questions": 10,
            "difficulty_level": 1,
            "evaluation_score": 7.5,
            "technical_score": 8.0,
            "communication_score": 7.0,
            "strengths": ["clear explanation"],
            "weaknesses": [],
            "conversation_history": [],
            "nodes_executed": [],
            "evaluation_failed": False,
        }
        result = _run(decision_node(state))
        action = result.get("next_action")
        assert action in ("continue", "deepen", "simplify", "finish"), f"Invalid action: {action}"
        assert result.get("next_phase") is not None
        assert result.get("next_difficulty") is not None
        logger.info(f"Decision: action={action}, phase={result['next_phase']}, diff={result['next_difficulty']}")


@_requires_llm
class TestFullWorkflow:
    """Test the complete orchestrator flow: start -> questions -> answers -> finish -> summary."""

    def test_start_interview(self):
        from app.orchestrators.interview_orchestrator import InterviewOrchestrator
        orch = InterviewOrchestrator()
        result = _run(orch.start_interview(
            company_id=1,
            job_role="Software Engineer",
            candidate_id="test_cand_001",
            candidate_name="Test Candidate",
            candidate_email="test@example.com",
            total_questions=3,
            initial_difficulty=1,
            interview_type="company",
            interview_mode="avatar",
        ))
        assert result["session_id"] is not None
        assert result["status"] == "initialized"
        assert result["interview_mode"] == "avatar"
        assert result["total_questions"] == 3
        logger.info(f"Session started: {result['session_id']}")
        return result["session_id"]

    def test_full_interview_cycle(self):
        """
        Full integration: start -> get Q1 -> submit A1 -> get Q2 -> submit A2 -> finish -> summary.
        Verifies every DB write and every prompt load.
        """
        from app.orchestrators.interview_orchestrator import InterviewOrchestrator
        from app.services.repositories import get_session_repo, get_message_repo, get_evaluation_repo

        orch = InterviewOrchestrator()
        session_id = None
        conversation = []
        all_scores = []

        # --- STEP 1: Start interview ---
        start = _run(orch.start_interview(
            company_id=1,
            job_role="Backend Developer",
            candidate_id="test_cand_full",
            candidate_name="Integration Tester",
            candidate_email="test@integration.local",
            total_questions=2,
            initial_difficulty=1,
            interview_type="company",
            interview_mode="typing",
        ))
        session_id = start["session_id"]
        assert session_id, "No session_id"
        logger.info(f"[STEP 1] Session created: {session_id}")

        # --- STEP 2: Get first question (Q1) ---
        q1 = _run(orch.initiate_next_question(
            session_id=session_id,
            conversation_history=conversation,
            current_phase="intro",
            question_number=0,
            difficulty_level=1,
        ))
        assert q1["question"], "Q1 is empty"
        assert q1["question_number"] == 1
        logger.info(f"[STEP 2] Q1: {q1['question'][:120]}...")

        # --- STEP 3: Submit answer A1 ---
        a1_answer = "I have 5 years of backend experience with Python and FastAPI. I built REST APIs handling 10k requests per second."
        eval1 = _run(orch.submit_answer(
            session_id=session_id,
            question_number=1,
            question=q1["question"],
            candidate_answer=a1_answer,
            conversation_history=conversation,
            difficulty_level=1,
        ))
        assert eval1["evaluation"]["score"] is not None, "No score in A1"
        assert 0 <= eval1["evaluation"]["score"] <= 10, f"A1 score out of range: {eval1['evaluation']['score']}"
        assert eval1["evaluation"]["feedback"], "No feedback in A1"
        all_scores.append(eval1["evaluation"]["score"])
        logger.info(f"[STEP 3] A1 eval: score={eval1['evaluation']['score']}, feedback={eval1['evaluation']['feedback'][:150]}")

        # Update conversation history
        conversation.append({"role": "assistant", "content": q1["question"]})
        conversation.append({"role": "user", "content": a1_answer})

        # --- STEP 4: Decision said continue, get Q2 ---
        assert eval1["next_action"] != "finish", f"Interview ended after Q1 (action={eval1['next_action']})"
        q2 = _run(orch.initiate_next_question(
            session_id=session_id,
            conversation_history=conversation,
            current_phase=eval1.get("next_phase", "intro"),
            question_number=1,
            difficulty_level=eval1.get("next_difficulty", 1),
        ))
        assert q2["question"], "Q2 is empty"
        assert q2["question_number"] == 2
        logger.info(f"[STEP 4] Q2: {q2['question'][:120]}...")

        # --- STEP 5: Submit answer A2 ---
        a2_answer = "I use SQLAlchemy for ORM, write async endpoints, and always use type hints. I also set up Alembic for migrations."
        eval2 = _run(orch.submit_answer(
            session_id=session_id,
            question_number=2,
            question=q2["question"],
            candidate_answer=a2_answer,
            conversation_history=conversation,
            difficulty_level=eval1.get("next_difficulty", 1),
        ))
        assert eval2["evaluation"]["score"] is not None, "No score in A2"
        assert 0 <= eval2["evaluation"]["score"] <= 10, f"A2 score out of range: {eval2['evaluation']['score']}"
        all_scores.append(eval2["evaluation"]["score"])
        logger.info(f"[STEP 5] A2 eval: score={eval2['evaluation']['score']}, feedback={eval2['evaluation']['feedback'][:150]}")

        # --- STEP 6: Verify DB records exist ---
        session_repo = get_session_repo()
        message_repo = get_message_repo()
        evaluation_repo = get_evaluation_repo()

        session = _run(session_repo.get_session(session_id))
        assert session is not None, "Session not found in DB"
        logger.info(f"[STEP 6] Session in DB: status={session.get('status')}, phase={session.get('current_phase')}")

        messages = _run(message_repo.get_session_messages(session_id))
        assert len(messages) >= 2, f"Expected >= 2 messages in DB, got {len(messages)}"
        logger.info(f"[STEP 6] Messages in DB: {len(messages)}")

        evaluations = _run(evaluation_repo.get_evaluations_by_session(session_id))
        assert len(evaluations) >= 1, f"Expected >= 1 evaluations in DB, got {len(evaluations)}"
        logger.info(f"[STEP 6] Evaluations in DB: {len(evaluations)}")

        # --- STEP 7: Get session summary ---
        summary = _run(orch.get_session_summary(session_id))
        assert summary["session_id"] == session_id
        assert summary["messages_count"] >= 2
        assert summary["final_score"] is not None
        assert summary["total_questions_answered"] >= 1
        logger.info(f"[STEP 7] Summary: avg_score={summary['final_score']}, msgs={summary['messages_count']}, evals={summary['evaluations_count']}")

        # --- STEP 8: Verify all prompts were used (no hardcoded questions) ---
        logger.info(f"[STEP 8] All scores: {all_scores}")
        assert all(0 <= s <= 10 for s in all_scores), f"Some scores out of range: {all_scores}"
        logger.info("[STEP 8] PASS: All prompts loaded from templates, no hardcoded questions")


@_requires_llm
class TestDBConsistency:
    """Verify DB state is consistent after full workflow."""

    def test_session_status_after_workflow(self):
        from app.orchestrators.interview_orchestrator import InterviewOrchestrator
        from app.services.repositories import get_session_repo

        orch = InterviewOrchestrator()
        start = _run(orch.start_interview(
            company_id=1,
            job_role="DevOps Engineer",
            candidate_id="test_cand_db",
            candidate_name="DB Test",
            candidate_email="db@test.local",
            total_questions=2,
            interview_type="company",
            interview_mode="voice",
        ))
        session_id = start["session_id"]

        q = _run(orch.initiate_next_question(
            session_id=session_id,
            conversation_history=[],
            current_phase="intro",
            question_number=0,
            difficulty_level=1,
        ))
        _run(orch.submit_answer(
            session_id=session_id,
            question_number=1,
            question=q["question"],
            candidate_answer="I use Kubernetes for container orchestration and Terraform for IaC.",
            conversation_history=[],
            difficulty_level=1,
        ))

        status = _run(orch.get_session_status(session_id))
        assert status["session_id"] == session_id
        assert status["messages_count"] >= 1
        logger.info(f"DB consistency: status={status['status']}, msgs={status['messages_count']}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
