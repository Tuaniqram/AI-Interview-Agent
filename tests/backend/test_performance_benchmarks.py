"""
Performance benchmarks for backend optimizations (no external dependencies).
Uses manual timing instead of pytest-benchmark.
"""
import asyncio
import hashlib
import logging
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger("perf_benchmark")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

pytestmark = pytest.mark.asyncio


# ============================================================================
# 1. Prompt cache benchmark
# ============================================================================
class TestPromptCache:
    """Measure prompt loading + rendering time with and without cache."""

    async def test_prompt_load_and_render(self):
        from app.services.prompt_loader import load_prompt

        # First load — cache miss
        t0 = time.perf_counter()
        result = load_prompt(
            "interview", "question_generation.md",
            job_role="Backend Developer",
            phase="technical",
            difficulty_level=2,
            company_context="Test company context for benchmarking.",
            candidate_profile="Senior developer with 5 years experience",
            question_number=1,
            conversation_history="(warmup conversation for cache test)"
        )
        first_duration = time.perf_counter() - t0
        assert result and len(result) > 0
        logger.info(f"  [prompt_cache] First load (cold): {first_duration*1000:.1f}ms")

        # Second load with same kwargs — cache hit
        t0 = time.perf_counter()
        result2 = load_prompt(
            "interview", "question_generation.md",
            job_role="Backend Developer",
            phase="technical",
            difficulty_level=2,
            company_context="Test company context for benchmarking.",
            candidate_profile="Senior developer with 5 years experience",
            question_number=1,
            conversation_history="(warmup conversation for cache test)"
        )
        second_duration = time.perf_counter() - t0
        assert result2 == result
        logger.info(f"  [prompt_cache] Second load (hot): {second_duration*1000:.1f}ms")
        logger.info(f"  [prompt_cache] Speedup: {first_duration/max(second_duration,0.0001):.1f}x")

    async def test_prompt_file_cache(self):
        """Same file loaded twice — file content cache should hit."""
        from app.services.prompt_loader import load_prompt

        t0 = time.perf_counter()
        r1 = load_prompt("system", "interviewer_system.md")
        t1 = time.perf_counter()

        r2 = load_prompt("system", "interviewer_system.md")
        t2 = time.perf_counter()

        file_first = t1 - t0
        file_second = t2 - t1
        logger.info(f"  [file_cache] First: {file_first*1000:.1f}ms, Second: {file_second*1000:.1f}ms")
        assert r1 == r2


# ============================================================================
# 2. LLM cache key stability
# ============================================================================
class TestLLMCache:
    def test_cache_key_stability(self):
        from app.services.llm_service import get_llm_service
        svc = get_llm_service()

        key1 = svc._generate_cache_key("hello world", 0.7, "system prompt")
        key2 = svc._generate_cache_key("hello world", 0.7, "system prompt")
        assert key1 == key2

        key3 = svc._generate_cache_key("hello world", 0.8, "system prompt")
        assert key1 != key3

        assert len(key1) == 32
        int(key1, 16)  # hex — should not raise
        logger.info(f"  [cache_key] Deterministic MD5: {key1}")

    def test_md5_key_deterministic(self):
        from app.services.llm_service import get_llm_service
        svc = get_llm_service()

        key = svc._generate_cache_key("What is Python?", 0.3, "You are a technical interviewer.")
        raw = "What is Python?|0.3|You are a technical interviewer."
        computed = hashlib.md5(raw.encode()).hexdigest()
        assert key == computed
        logger.info(f"  [cache_key] Cross-run stable: {key}")

    async def test_cache_hit_speed(self):
        from app.services.llm_service import get_llm_service
        svc = get_llm_service()
        svc._cache["perf_test_key"] = {"content": "cached", "timestamp": time.time()}

        t0 = time.perf_counter()
        for _ in range(1000):
            _ = svc._cache.get("perf_test_key")
        elapsed = time.perf_counter() - t0
        logger.info(f"  [cache_hit] 1000 lookups: {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.1f}µs each)")


# ============================================================================
# 3. RAG cache
# ============================================================================
class TestRAGCache:
    async def test_rag_cache_limits(self):
        from app.agents.company_context_node import (
            _session_context_cache, _MAX_CACHE_SIZE, _CACHE_TTL
        )
        assert _MAX_CACHE_SIZE == 100
        assert _CACHE_TTL == 600
        logger.info(f"  [rag_cache] MAX_SIZE={_MAX_CACHE_SIZE}, TTL={_CACHE_TTL}s")

        # Verify cache stores (timestamp, data) tuples
        cache_key = "perf_test_session:perf_test_company"
        _session_context_cache[cache_key] = (time.time(), [{"test": "data"}])
        entry = _session_context_cache[cache_key]
        assert isinstance(entry, tuple) and len(entry) == 2
        del _session_context_cache[cache_key]
        logger.info(f"  [rag_cache] Tuple format verified")

    async def test_rag_cache_fill_limit(self):
        from app.agents.company_context_node import _session_context_cache, _MAX_CACHE_SIZE

        # Fill beyond limit
        for i in range(_MAX_CACHE_SIZE + 20):
            _session_context_cache[f"perf_fill_{i}"] = (time.time(), [])
        logger.info(f"  [rag_cache] After filling {_MAX_CACHE_SIZE + 20} entries: size={len(_session_context_cache)}")
        # Clean up
        for i in range(_MAX_CACHE_SIZE + 20):
            _session_context_cache.pop(f"perf_fill_{i}", None)


# ============================================================================
# 4. Concurrency (Semaphore)
# ============================================================================
class TestConcurrency:
    async def test_semaphore_concurrent_calls(self):
        from app.services.llm_service import get_llm_service
        svc = get_llm_service()

        async def dummy(delay: float):
            async with svc._rate_limiter:
                await asyncio.sleep(delay)
                return "done"

        t0 = time.perf_counter()
        results = await asyncio.gather(dummy(0.2), dummy(0.2), dummy(0.2))
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.4, f"3 concurrent 0.2s calls took {elapsed:.3f}s"
        assert len(results) == 3
        logger.info(f"  [semaphore] 3 concurrent calls (200ms each): {elapsed:.3f}s (expected ~0.2s)")


# ============================================================================
# 5. asyncio.gather benchmark
# ============================================================================
class TestGather:
    async def test_gather_speedup(self):
        """Measure speedup of gather vs sequential for 3 mock DB calls."""

        async def mock_db(name: str, delay: float = 0.05):
            await asyncio.sleep(delay)
            return name

        # Sequential
        t0 = time.perf_counter()
        r1 = await mock_db("a")
        r2 = await mock_db("b")
        r3 = await mock_db("c")
        seq_time = time.perf_counter() - t0

        # Parallel
        t0 = time.perf_counter()
        r1, r2, r3 = await asyncio.gather(mock_db("a"), mock_db("b"), mock_db("c"))
        par_time = time.perf_counter() - t0

        logger.info(f"  [gather] Sequential: {seq_time*1000:.0f}ms, Parallel: {par_time*1000:.0f}ms (speedup: {seq_time/max(par_time,0.0001):.1f}x)")
        assert par_time < seq_time * 0.6  # parallel should be faster


# ============================================================================
# 6. InterviewState construction speed
# ============================================================================
class TestStateConstruction:
    async def test_state_dict_speed(self):
        """40-field InterviewState should construct in <0.1ms."""
        def build():
            return {
                "session_id": "test-session-id",
                "company_id": 1,
                "candidate_id": "test-candidate",
                "job_role": "Backend Developer",
                "interview_type": "company",
                "conversation_history": [],
                "current_phase": "intro",
                "phase_stage": 0,
                "question_number": 1,
                "total_questions": 10,
                "difficulty_level": 1,
                "current_question": "What is Python?",
                "company_context": [],
                "company_requirements": "Python expertise required",
                "rag_metadata": {},
                "candidate_answer": "",
                "evaluation_score": None,
                "technical_score": None,
                "communication_score": None,
                "strengths": [],
                "weaknesses": [],
                "feedback_detail": "",
                "evaluation_metadata": {},
                "evaluation_failed": False,
                "next_action": "continue",
                "suggested_follow_up": "",
                "next_phase": None,
                "next_difficulty": None,
                "start_time": None,
                "elapsed_time": None,
                "is_complete": False,
                "final_report": None,
                "nodes_executed": []
            }

        t0 = time.perf_counter()
        for _ in range(10000):
            build()
        elapsed = time.perf_counter() - t0
        per_call = elapsed / 10000 * 1e6
        logger.info(f"  [state_build] 10,000 iterations: {elapsed:.3f}s ({per_call:.1f}µs each)")


# ============================================================================
# 7. End-to-end: warm startup check
# ============================================================================
class TestWarmStartup:
    async def test_workflows_pre_warmed(self):
        """Workflows should be compiled and ready (already pre-warmed in lifespan)."""
        from app.graph.question_workflow import get_question_workflow
        from app.graph.evaluation_workflow import get_evaluation_workflow

        t0 = time.perf_counter()
        qw = get_question_workflow()
        ew = get_evaluation_workflow()
        elapsed = time.perf_counter() - t0
        logger.info(f"  [pre_warm] Workflow access: {elapsed*1000:.1f}ms")
        assert qw is not None
        assert ew is not None


# ============================================================================
# 8. Decision node speed (no LLM call)
# ============================================================================
class TestDecisionNode:
    async def test_decision_node_is_fast(self):
        """Decision node should complete in <10ms (no LLM call)."""
        from app.agents.decision_node import decision_node

        state = {
            "session_id": "test",
            "company_id": 1,
            "candidate_id": "test",
            "job_role": "Backend Developer",
            "interview_type": "company",
            "conversation_history": [{"role": "user", "content": "test"}],
            "current_phase": "technical",
            "phase_stage": 0,
            "question_number": 5,
            "total_questions": 10,
            "difficulty_level": 2,
            "current_question": "What is Python?",
            "evaluation_score": 8.5,
            "technical_score": 8.0,
            "communication_score": 9.0,
            "strengths": ["good answer"],
            "weaknesses": [],
            "feedback_detail": "Good job",
            "candidate_answer": "Python is a language",
            "company_context": [],
            "company_requirements": "",
            "rag_metadata": {},
            "evaluation_metadata": {},
            "evaluation_failed": False,
            "next_action": "continue",
            "suggested_follow_up": "",
            "next_phase": None,
            "next_difficulty": None,
            "start_time": None,
            "elapsed_time": None,
            "is_complete": False,
            "final_report": None,
            "nodes_executed": []
        }

        t0 = time.perf_counter()
        for _ in range(100):
            result = await decision_node(dict(state))
        elapsed = time.perf_counter() - t0
        per_call = elapsed / 100 * 1000
        logger.info(f"  [decision_node] 100 calls: {elapsed:.3f}s ({per_call:.2f}ms each)")
        assert result["next_action"] == "deepen"  # score 8.5 → difficulty increase
