"""
Backend API Integration Test — HTTP Endpoint Testing
Tests all interview endpoints via httpx.AsyncClient against the FastAPI app.
Real DB (Supabase) + real LLM (OpenRouter) — no mocks.

Usage:
  cd D:\projectiqram\AI\AI-Interview-Agent
  .\venv\Scripts\python -m pytest tests/backend/test_api_endpoints.py -v -s

  # Health checks only (instant, no AI/DB):
  .\venv\Scripts\python -m pytest tests/backend/test_api_endpoints.py -v -s -k "Health or Root"

  # Full interview flow (4 questions, ~5 min):
  .\venv\Scripts\python -m pytest tests/backend/test_api_endpoints.py::TestFullInterviewFlow -v -s

  # Error handling only:
  .\venv\Scripts\python -m pytest tests/backend/test_api_endpoints.py -v -s -k "404 or 422"

Requires:
  - .env with SUPABASE_URL, SUPABASE_KEY, PINECONE_API_KEY, OPENROUTER_API_KEY
  - FastAPI app importable from app.main
"""
import logging
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api_test")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """Async HTTP client — in-process, no server needed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def started_session(client):
    """Start an interview with 4 questions, return (session_id, response_json)."""
    resp = await client.post("/interviews", json={
        "company_id": 1,
        "job_role": "Backend Developer",
        "candidate_name": "API Test User",
        "candidate_email": "api@test.local",
        "total_questions": 4,
        "initial_difficulty": 1,
        "interview_type": "company",
        "interview_mode": "typing",
    })
    assert resp.status_code == 200, f"Start failed: {resp.status_code} {resp.text}"
    data = resp.json()
    return data["session_id"], data


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Instant tests — no AI, no DB."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body or "message" in body

    @pytest.mark.asyncio
    async def test_root_returns_running(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert "AI Interview Agent" in str(body)


class TestInterviewStart:
    """POST /interviews — start a new interview session."""

    @pytest.mark.asyncio
    async def test_start_interview_200(self, client):
        resp = await client.post("/interviews", json={
            "company_id": 1,
            "job_role": "Backend Developer",
            "candidate_name": "Start Test",
            "total_questions": 4,
            "interview_mode": "typing",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["status"] == "initialized"
        assert data["current_phase"] == "intro"
        assert data["question_number"] == 0
        assert data["total_questions"] == 4
        assert data["interview_mode"] == "typing"
        logger.info(f"Start test passed: session={data['session_id']}")

    @pytest.mark.asyncio
    async def test_start_interview_422_missing_fields(self, client):
        resp = await client.post("/interviews", json={})
        assert resp.status_code == 422


class TestQuestionGeneration:
    """POST /interviews/{id}/questions/next — generate the next question."""

    @pytest.mark.asyncio
    async def test_get_next_question_200(self, client, started_session):
        session_id, _ = started_session
        resp = await client.post(f"/interviews/{session_id}/questions/next", json={
            "conversation_history": [],
            "current_phase": "intro",
            "question_number": 0,
            "difficulty_level": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["question"], "Question is empty"
        assert len(data["question"]) > 10
        assert data["question_number"] >= 1
        assert "phase" in data
        logger.info(f"Q1: {data['question'][:100]}...")


class TestAnswerSubmission:
    """POST /interviews/{id}/answers — submit an answer for evaluation."""

    @pytest.mark.asyncio
    async def test_submit_answer_200(self, client, started_session):
        session_id, _ = started_session
        q_resp = await client.post(f"/interviews/{session_id}/questions/next", json={
            "current_phase": "intro",
            "question_number": 0,
            "difficulty_level": 1,
        })
        question_data = q_resp.json()

        resp = await client.post(f"/interviews/{session_id}/answers", json={
            "question_number": question_data["question_number"],
            "question": question_data["question"],
            "candidate_answer": "I have 5 years of backend experience with Python and FastAPI.",
            "conversation_history": [],
            "difficulty_level": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "evaluation" in data
        ev = data["evaluation"]
        assert ev["score"] is not None
        assert 0 <= ev["score"] <= 10
        assert ev["feedback"], "No feedback"
        assert "next_action" in data
        logger.info(f"A1 eval: score={ev['score']}, action={data['next_action']}")


class TestSessionStatus:
    """GET /interviews/{id}/status — check session status."""

    @pytest.mark.asyncio
    async def test_session_status(self, client, started_session):
        session_id, _ = started_session
        resp = await client.get(f"/interviews/{session_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert "status" in data
        assert "messages_count" in data


class TestSessionSummary:
    """GET /interviews/{id}/summary — get session summary."""

    @pytest.mark.asyncio
    async def test_session_summary(self, client, started_session):
        session_id, _ = started_session
        resp = await client.get(f"/interviews/{session_id}/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert "final_score" in data
        assert "total_questions_answered" in data
        assert "messages" in data
        assert "evaluations" in data


class TestRagStatus:
    """GET /interviews/{id}/rag-status — RAG metadata."""

    @pytest.mark.asyncio
    async def test_rag_status(self, client, started_session):
        session_id, _ = started_session
        resp = await client.get(f"/interviews/{session_id}/rag-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "rag_available" in data


class TestErrorHandling:
    """Error cases — nonexistent sessions."""

    @pytest.mark.asyncio
    async def test_question_nonexistent_session_404(self, client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        resp = await client.post(f"/interviews/{fake_uuid}/questions/next", json={
            "current_phase": "intro",
            "question_number": 0,
            "difficulty_level": 1,
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_answer_nonexistent_session_404(self, client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        resp = await client.post(f"/interviews/{fake_uuid}/answers", json={
            "question_number": 1,
            "question": "Test question?",
            "candidate_answer": "Test answer",
            "difficulty_level": 1,
        })
        assert resp.status_code == 404


class TestFullInterviewFlow:
    """
    THE BIG ONE: Complete 4-question interview via HTTP API.
    start -> Q1 -> A1 -> Q2 -> A2 -> status -> summary -> RAG.
    Tests phase transitions, scoring, and summary completeness.
    """

    @pytest.mark.asyncio
    async def test_complete_4_question_interview(self, client):
        conversation = []

        # --- STEP 1: Start interview (4 questions) ---
        start_resp = await client.post("/interviews", json={
            "company_id": 1,
            "job_role": "Backend Developer",
            "candidate_name": "Full Flow Tester",
            "candidate_email": "fullflow@test.local",
            "total_questions": 4,
            "initial_difficulty": 1,
            "interview_type": "company",
            "interview_mode": "typing",
        })
        assert start_resp.status_code == 200
        session = start_resp.json()
        session_id = session["session_id"]
        logger.info(f"[STEP 1] Session: {session_id}")

        # --- STEP 2: Get Q1 ---
        q1_resp = await client.post(f"/interviews/{session_id}/questions/next", json={
            "conversation_history": conversation,
            "current_phase": "intro",
            "question_number": 0,
            "difficulty_level": 1,
        })
        assert q1_resp.status_code == 200
        q1 = q1_resp.json()
        assert q1["question"], "Q1 is empty"
        logger.info(f"[STEP 2] Q1 (#{q1['question_number']}): {q1['question'][:100]}...")

        # --- STEP 3: Submit A1 ---
        a1_answer = "I have 5 years of backend experience with Python and FastAPI. I built REST APIs handling 10k requests per second with async endpoints, SQLAlchemy ORM, and Alembic migrations."
        a1_resp = await client.post(f"/interviews/{session_id}/answers", json={
            "question_number": q1["question_number"],
            "question": q1["question"],
            "candidate_answer": a1_answer,
            "conversation_history": conversation,
            "difficulty_level": 1,
        })
        assert a1_resp.status_code == 200
        ev1 = a1_resp.json()
        assert ev1["evaluation"]["score"] is not None
        assert 0 <= ev1["evaluation"]["score"] <= 10
        logger.info(f"[STEP 3] A1: score={ev1['evaluation']['score']}, action={ev1['next_action']}")

        conversation.append({"role": "assistant", "content": q1["question"]})
        conversation.append({"role": "user", "content": a1_answer})

        # --- STEP 4: Get Q2 ---
        q2_resp = await client.post(f"/interviews/{session_id}/questions/next", json={
            "conversation_history": conversation,
            "current_phase": ev1.get("next_phase", "intro"),
            "question_number": 1,
            "difficulty_level": ev1.get("next_difficulty", 1),
        })
        assert q2_resp.status_code == 200
        q2 = q2_resp.json()
        assert q2["question"], "Q2 is empty"
        logger.info(f"[STEP 4] Q2 (#{q2['question_number']}): {q2['question'][:100]}...")

        # --- STEP 5: Submit A2 ---
        a2_answer = "I use SQLAlchemy for ORM, write async endpoints with type hints, and set up Alembic for database migrations. I also implement comprehensive error handling and logging."
        a2_resp = await client.post(f"/interviews/{session_id}/answers", json={
            "question_number": q2["question_number"],
            "question": q2["question"],
            "candidate_answer": a2_answer,
            "conversation_history": conversation,
            "difficulty_level": ev1.get("next_difficulty", 1),
        })
        assert a2_resp.status_code == 200
        ev2 = a2_resp.json()
        assert ev2["evaluation"]["score"] is not None
        assert 0 <= ev2["evaluation"]["score"] <= 10
        logger.info(f"[STEP 5] A2: score={ev2['evaluation']['score']}, action={ev2['next_action']}")

        conversation.append({"role": "assistant", "content": q2["question"]})
        conversation.append({"role": "user", "content": a2_answer})

        # --- STEP 6: Get status ---
        status_resp = await client.get(f"/interviews/{session_id}/status")
        assert status_resp.status_code == 200
        status = status_resp.json()
        assert status["session_id"] == session_id
        logger.info(f"[STEP 6] Status: messages={status['messages_count']}")

        # --- STEP 7: Get summary ---
        summary_resp = await client.get(f"/interviews/{session_id}/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert summary["session_id"] == session_id
        assert summary["total_questions_answered"] >= 1
        assert len(summary["messages"]) >= 1
        assert len(summary["evaluations"]) >= 1
        logger.info(f"[STEP 7] Summary: score={summary['final_score']}, msgs={summary['messages_count']}, evals={summary['evaluations_count']}")

        # --- STEP 8: Get RAG status ---
        rag_resp = await client.get(f"/interviews/{session_id}/rag-status")
        assert rag_resp.status_code == 200
        rag = rag_resp.json()
        assert "rag_available" in rag
        logger.info(f"[STEP 8] RAG: available={rag['rag_available']}")

        logger.info(f"[COMPLETE] Full interview flow passed! session={session_id}")
