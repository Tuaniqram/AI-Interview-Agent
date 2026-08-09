import pytest

from app.config.interview_styles import get_style
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY

EVALUATOR_JSON = {
    "technical": {"score": 8.0, "evidence": "solid", "confidence": 0.9, "strengths": ["a"], "weaknesses": []},
    "communication": {"score": 7.0, "evidence": "clear", "confidence": 0.8, "strengths": [], "weaknesses": ["b"]},
    "reasoning": {"score": 6.5, "evidence": "ok", "confidence": 0.7, "strengths": [], "weaknesses": []},
    "behavioral": {"score": None, "evidence": "n/a", "confidence": 0.0, "strengths": [], "weaknesses": []},
    "confidence": {"score": 7.5, "evidence": "sure", "confidence": 0.8, "strengths": [], "weaknesses": []},
    "completeness": {"score": 8.5, "evidence": "full", "confidence": 0.85, "strengths": [], "weaknesses": []},
    "observations": {"verbosity": 0.3, "hedging": 0.1},
    "composite_score": 7.6,
}

STRATEGY_JSON = (
    '{"phase_order": ["technical"], "competency_priority": {}, "difficulty_range": [1, 3], '
    '"persona": "friendly", "strategic_intent": "test", "early_termination_threshold": 0.85}'
)

SYNTHESIS_JSON = (
    '{"holistic_score": 7.4, "narrative": "A solid candidate.", "key_strengths": ["Communicates clearly"], '
    '"key_weaknesses": ["Depth of tradeoff analysis"], "fit_assessment": "Good Fit", "interview_notes": "note"}'
)

ZERO_EVAL_JSON = (
    '{"technical": {"score": 0.0, "evidence": "no", "confidence": 0.9, "strengths": [], "weaknesses": []}, '
    '"communication": {"score": 0.0, "evidence": "no", "confidence": 0.9, "strengths": [], "weaknesses": []}, '
    '"reasoning": {"score": 0.0, "evidence": "no", "confidence": 0.9, "strengths": [], "weaknesses": []}, '
    '"behavioral": {"score": 0.0, "evidence": "no", "confidence": 0.9, "strengths": [], "weaknesses": []}, '
    '"confidence": {"score": 0.0, "evidence": "no", "confidence": 0.9, "strengths": [], "weaknesses": []}, '
    '"completeness": {"score": 0.0, "evidence": "no", "confidence": 0.9, "strengths": [], "weaknesses": []}, '
    '"composite_score": 0.0}'
)

GOVERNOR_JSON = '{"delta": 0, "rationale": "keeping steady", "scaffold": ""}'

CONDUCTOR_TURN_JSON = (
    '{"acknowledgement": "Got it.", "bridge": "Let me dig into that.", '
    '"question": "Walk me through a concrete example of that."}'
)


def refutable_hypotheses(n: int = 6) -> list[dict]:
    """Hypotheses in 'testing' whose statements embed the target competency id,
    so update_hypotheses computes relevance and refutes them on zero scores."""
    return [
        {
            "id": f"h{i}",
            "competency": "tech_core",
            "statement": "Candidate has strong tech_core skills",
            "direction": "positive",
            "confidence": 0.0,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "status": "testing",
        }
        for i in range(n)
    ]


class StubLLM:
    """Recorded-invocation LLM stub. Returns responses in order, or fails on demand."""

    def __init__(self, response=None, responses=None, fail=False):
        self.response = response
        self.responses = list(responses or [])
        self.fail = fail
        self.calls = []

    async def invoke(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        if self.fail:
            raise Exception("stub LLM failure")
        if self.responses:
            return self.responses.pop(0)
        return self.response


@pytest.fixture
def stub_llm(monkeypatch):
    """Patch get_llm_service with a StubLLM; returns the stub."""

    def factory(**kwargs):
        stub = StubLLM(**kwargs)
        monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: stub)
        return stub

    return factory


@pytest.fixture
def fake_evidence_repo(monkeypatch):
    """Neutralize the evidence DB writes inside evidence_extractor_node."""

    class FakeRepo:
        def __init__(self):
            self.saved = []

        async def create_evidence(self, **kwargs):
            self.saved.append(kwargs)

    fake = FakeRepo()
    monkeypatch.setattr("app.repositories.evidence_repository.EvidenceRepository", FakeRepo)
    return fake


@pytest.fixture
def fake_repos(monkeypatch):
    """In-memory stand-ins for the session/message/evaluation repositories,
    installed on the Repositories factory class used by the engine's
    persistence layer."""
    from uuid import uuid4
    from app.services import repositories as repo_factory

    class FakeMessageRepo:
        def __init__(self):
            self.questions = []
            self.answers = []

        async def create_question(self, session_id, question_text, question_number, phase):
            row = {
                "id": uuid4(),
                "session_id": session_id,
                "role": "interviewer",
                "message_type": "question",
                "content": question_text,
                "question_number": question_number,
                "phase": phase,
            }
            self.questions.append(row)
            return row

        async def create_candidate_answer(self, session_id, role, candidate_answer,
                                          question_number, phase, score):
            row = {
                "id": uuid4(),
                "session_id": session_id,
                "role": role,
                "message_type": "candidate_answer",
                "content": candidate_answer,
                "question_number": question_number,
                "phase": phase,
                "score": score,
            }
            self.answers.append(row)
            return row

    class FakeEvaluationRepo:
        def __init__(self):
            self.saved = []

        async def create_evaluation(self, session_id, message_id, technical_score,
                                    communication_score, strengths, weaknesses,
                                    feedback, overall_score):
            row = {
                "session_id": session_id,
                "message_id": message_id,
                "technical_score": technical_score,
                "communication_score": communication_score,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "feedback": feedback,
                "overall_score": overall_score,
            }
            self.saved.append(row)
            return row

    class FakeSessionRepo:
        def __init__(self):
            self.completions = []

        async def complete_session(self, session_id, final_score, final_feedback,
                                   ended_at=None, engine_version=None):
            row = {
                "session_id": session_id,
                "final_score": final_score,
                "final_feedback": final_feedback,
                "ended_at": ended_at,
                "engine_version": engine_version,
            }
            self.completions.append(row)
            return row

    messages = FakeMessageRepo()
    evaluations = FakeEvaluationRepo()
    sessions = FakeSessionRepo()
    monkeypatch.setattr(repo_factory.Repositories, "_message_repository", messages)
    monkeypatch.setattr(repo_factory.Repositories, "_evaluation_repository", evaluations)
    monkeypatch.setattr(repo_factory.Repositories, "_session_repository", sessions)
    return {"messages": messages, "evaluations": evaluations, "sessions": sessions}


STUB_COMPANY_BRAIN = {
    "version": "v1",
    "department_id": None,
    "job_role": "Software Engineer",
    "tech_stack": [],
    "culture": [],
    "challenges": [],
    "summary": "",
    "rag_metadata": {"success": False, "documents_retrieved": 0, "reason": "test-stub"},
    "source": "test-stub",
}


def make_intelligence_bundle(**overrides) -> dict:
    """Deterministic V5 intelligence bundle — no LLM/RAG artifacts."""
    bundle = {
        "company_brain": dict(STUB_COMPANY_BRAIN),
        "interview_blueprint": {
            "source": "test-stub",
            "job_role": "Software Engineer",
            "phases": [],
            "priority_competencies": [],
        },
        "candidate_brain": {
            "full_name": "Candidate",
            "skills": [],
            "strengths": [],
            "weaknesses": [],
            "source": "test-stub",
        },
        "initial_hypotheses": [],
        "evidence_requirements": [],
        "candidate_assessment": {
            "match_score": 0.0,
            "signal_strength": 0,
            "strong_areas": [],
            "gap_areas": [],
            "competency_coverage": {},
            "recommended_probes": [],
            "risk_signals": [],
        },
    }
    bundle.update(overrides)
    return bundle


@pytest.fixture
def stub_intelligence(monkeypatch):
    """Neutralize the V5 intelligence layer (LLM/RAG + company cache) so
    session start is deterministic. Patches both the intelligence builder used
    by ``InterviewEngine.start_session`` and the WS company-brain cache."""
    async def _stub_build(**kwargs):
        return make_intelligence_bundle()

    async def _stub_company_brain(**kwargs):
        return dict(STUB_COMPANY_BRAIN)

    monkeypatch.setattr(
        "app.intelligence.build_interview_intelligence",
        _stub_build,
    )
    monkeypatch.setattr(
        "app.api.interview_ws.get_or_build_company_brain",
        _stub_company_brain,
    )


def make_v4_state(**overrides) -> dict:
    """Mirror of the seed dict used by _build_v4_state / start_public_interview."""
    state = {
        "session_id": "session-1",
        "job_role": "Software Engineer",
        "department_id": None,
        "interview_style": get_style("STANDARD"),
        "persona": "friendly",
        "difficulty_level": 1,
        "candidate_profile": {"full_name": "Test Candidate", "headline": "", "strengths": [], "weaknesses": []},
        "competency_taxonomy": COMPETENCY_TAXONOMY,
        "domain_label": "Technical Knowledge",
        "required_competencies": [c["id"] for c in COMPETENCY_TAXONOMY],
        "conversation_history": [],
        "question_number": 0,
        "current_question": "",
        "candidate_answer": "",
        "flow_type": "v4_evidence_driven",
        "nodes_executed": [],
        "start_time": "2026-01-01T00:00:00+00:00",
        "hypotheses": [],
        "hypothesis_target": None,
        "evidence_store": [],
        "competency_summary": {},
        "unified_evaluation": {},
        "evaluation_score": None,
        "observations": [],
        "competency_plan": [],
        "next_competency": None,
        "interview_strategy": {},
        "reflection_action": "probe",
        "evidence_sufficiency": {},
        "hiring_recommendation": {},
        "contradictions": [],
        "consistency_checks": [],
        "extracted_evidence": [],
        "max_questions": 14,
        "questions_asked": [],
        "question_objective": {},
        "skip_evaluation": False,
        "evaluator_mode": "unified",
        "strategy_cache_valid": False,
    }
    state.update(overrides)
    return state
