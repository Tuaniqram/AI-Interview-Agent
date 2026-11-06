"""V5 intelligence module tests — company/candidate intelligence builders,
scorecard resolver, resume analyzer, matcher, and engine injection. All run
offline (deterministic fallbacks); the LLM paths are exercised through the
shared stub_llm fixture."""
import json

from app.engine.engine import InterviewEngine
from app.intelligence import build_interview_intelligence
from app.intelligence.candidate_intelligence_builder import (
    build_candidate_intelligence,
)
from app.intelligence.candidate_matcher import match_candidate_to_role
from app.intelligence.company_intelligence_builder import build_company_brain
from app.intelligence.document_analyzer import analyze_documents
from app.intelligence.interview_blueprint_builder import build_interview_blueprint
from app.intelligence.resume_analyzer import analyze_resume
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.intelligence.scorecard_resolver import resolve_evidence_requirements
from app.intelligence.persist import persist_intelligence_bundle
from app.models.db import (
    CandidateBrain as CandidateBrainRecord,
    CandidateEvidenceRequirement as RequirementRecord,
    CompanyBrain as CompanyBrainRecord,
    InterviewBlueprint as BlueprintRecord,
    Scorecard as ScorecardRecord,
)
from app.services.v4_session_store import MemoryV4SessionStore
from tests.conftest import STRATEGY_JSON, make_v4_state

BLUEPRINT_JSON = json.dumps(
    {
        "phases": ["intro", "technical", "behavioral", "conclusion"],
        "priority_competencies": [
            {"id": "tech_core", "name": "Core Language Proficiency", "weight": 0.9}
        ],
        "focus_areas": ["distributed systems"],
        "probe_strategy": {"depth": "adaptive", "max_follow_ups": 2, "style": "evidence-first"},
        "tech_stack_focus": ["kubernetes"],
        "scenarios": ["Design a system for X"],
    }
)


# ---------------------------------------------------------------------------
# document_analyzer / company_intelligence_builder
# ---------------------------------------------------------------------------

def test_analyze_documents_extracts_keywords():
    docs = [
        {"page_content": "We are a fintech startup using python, kubernetes and postgresql. "
                         "Our culture values ownership and transparency."},
        {"page_content": "Our engineering challenges include scaling incidents and technical debt."},
    ]
    result = analyze_documents(docs, job_role="Backend Engineer")
    assert "python" in result["tech_stack"]
    assert "kubernetes" in result["tech_stack"]
    assert "postgresql" in result["tech_stack"]
    assert "ownership" in result["culture"]
    assert any("challenge" in c.lower() or "incident" in c.lower() for c in result["challenges"])
    assert result["summary"]


async def test_build_company_brain_uses_provided_documents():
    docs = [
        {"page_content": "We build with python, aws and docker. "
                         "Agile sprints with code review and on-call."},
    ]
    brain = await build_company_brain(department_id=7, job_role="Backend", documents=docs, use_llm=False)
    assert brain["department_id"] == 7
    assert brain["documents_analyzed"] == 1
    assert brain["source"] == "fallback"
    assert "python" in brain["tech_stack"]
    assert "agile" in brain["process"]
    assert brain["rag_metadata"]["documents_retrieved"] == 1


async def test_build_company_brain_without_department_is_empty_but_valid():
    brain = await build_company_brain(department_id=None, job_role="Backend", use_rag=False, use_llm=False)
    assert brain["source"] == "fallback"
    assert brain["tech_stack"] == []
    assert brain["rag_metadata"]["success"] is False


# ---------------------------------------------------------------------------
# scorecard_resolver
# ---------------------------------------------------------------------------

def test_resolve_evidence_requirements_from_scorecard_competencies():
    reqs = resolve_evidence_requirements(
        [
            {"id": "tech_core", "name": "Core Language Proficiency", "weight": 2.0},
            {"id": "behav_communication", "name": "Communication", "weight": 1.0},
        ]
    )
    assert len(reqs) == 2
    assert reqs[0]["competency"] == "tech_core"
    assert reqs[0]["weight"] == 2.0
    assert reqs[0]["verification_probe"]
    assert reqs[1]["competency"] == "behav_communication"


def test_resolve_evidence_requirements_defaults_to_taxonomy_and_caps():
    reqs = resolve_evidence_requirements(None, max_requirements=5)
    assert len(reqs) == 5
    assert all(r["min_evidence"] >= 1 for r in reqs)


# ---------------------------------------------------------------------------
# interview_blueprint_builder
# ---------------------------------------------------------------------------

async def test_blueprint_fallback_is_functional():
    bp = await build_interview_blueprint(
        job_role="Backend Engineer",
        required_competencies=["tech_core", "tech_db"],
        use_llm=False,
    )
    assert bp["source"] == "fallback"
    assert bp["job_role"] == "Backend Engineer"
    assert bp["phases"]
    assert bp["priority_competencies"]


async def test_blueprint_llm_enrichment(stub_llm):
    stub = stub_llm(response=BLUEPRINT_JSON)
    bp = await build_interview_blueprint(
        job_role="Backend Engineer",
        company_brain={"tech_stack": ["kubernetes"]},
        use_llm=True,
    )
    assert bp["source"] == "llm"
    assert bp["tech_stack_focus"] == ["kubernetes"]
    assert stub.calls[0]["prompt"]


# ---------------------------------------------------------------------------
# resume_analyzer / candidate_matcher / candidate_intelligence_builder
# ---------------------------------------------------------------------------

async def test_resume_analyzer_heuristics():
    resume = (
        "Jane Doe\nSenior Backend Engineer — Python, Django, PostgreSQL\n"
        "8+ years building distributed systems with Docker and AWS."
    )
    data = await analyze_resume(resume, job_role="Backend Engineer", use_llm=False)
    assert data["source"] == "heuristics"
    assert "python" in data["skills"]
    assert "postgresql" in data["skills"]
    assert data["years_of_experience"] == 8


async def test_resume_analyzer_merges_profile():
    data = await analyze_resume(
        "",
        job_role="Backend Engineer",
        candidate_profile={"full_name": "Jane", "headline": "Backend dev", "skills": ["python"]},
        use_llm=False,
    )
    assert data["source"] == "profile"
    assert data["full_name"] == "Jane"
    assert "python" in data["skills"]


async def test_resume_analyzer_dspy_branch_merges_typed_output(monkeypatch):
    """The DSPy branch returns a typed dict; the merge + source=resume_llm are
    identical to the old parse_llm_json_with_retry path."""
    async def fake_run(resume_text, job_role):
        return {
            "full_name": "Jane Doe",
            "headline": "Backend dev",
            "skills": ["python", "postgresql", "python"],
            "strengths": ["python"],
            "weaknesses": [],
            "experience": ["Backend Engineer at X (2020 - Present)"],
            "education": ["B.S. CS, UW (2014-2018)"],
            "years_of_experience": "8+ years",
        }

    monkeypatch.setattr("app.intelligence.dspy_modules.run_resume_analysis", fake_run)
    data = await analyze_resume(
        "Jane Doe\nBackend Engineer - Python, PostgreSQL\n8+ years experience.",
        job_role="Backend Engineer",
        use_llm=True,
    )
    assert data["source"] == "resume_llm"
    assert data["full_name"] == "Jane Doe"
    assert "python" in data["skills"]
    assert data["skills"].count("python") == 1  # dedupe still applies
    assert data["years_of_experience"] == 8  # _coerce_years still applies


async def test_resume_analyzer_dspy_branch_falls_back_to_heuristics(monkeypatch):
    """When the DSPy call raises (LM unreachable), behavior is byte-identical
    to today: heuristics, source='heuristics'."""

    async def boom(resume_text, job_role):
        raise RuntimeError("LM unreachable")

    monkeypatch.setattr("app.intelligence.dspy_modules.run_resume_analysis", boom)
    data = await analyze_resume(
        "Jane Doe\nSenior Backend Engineer - Python, Django, PostgreSQL\n"
        "8+ years building distributed systems with Docker and AWS.",
        job_role="Backend Engineer",
        use_llm=True,
    )
    assert data["source"] == "heuristics"
    assert "python" in data["skills"]
    assert data["years_of_experience"] == 8


async def test_resume_analyzer_legacy_backend_when_env_legacy(monkeypatch):
    """RESUME_LLM_BACKEND=legacy routes to the old prompt-loader path; the DSPy
    path must NOT be touched."""
    from app.intelligence import resume_analyzer

    async def fake_legacy(text, job_role):
        return {
            "full_name": "Jane Doe",
            "headline": "Backend dev",
            "skills": ["python", "python"],
            "strengths": [],
            "weaknesses": [],
            "experience": [],
            "education": [],
            "years_of_experience": "8+ years",
        }

    called = {"dspy": False}

    async def fake_dspy(resume_text, job_role):
        called["dspy"] = True
        return {}

    monkeypatch.setenv("RESUME_LLM_BACKEND", "legacy")
    monkeypatch.setattr("app.intelligence.dspy_modules.run_resume_analysis", fake_dspy)
    monkeypatch.setattr("app.intelligence.resume_analyzer._legacy_llm_parse", fake_legacy)

    data = await analyze_resume(
        "Jane Doe\nBackend Engineer - Python, PostgreSQL\n8+ years experience.",
        job_role="Backend Engineer",
        use_llm=True,
    )
    assert data["source"] == "resume_llm"
    assert data["full_name"] == "Jane Doe"
    assert data["skills"] == ["python"]
    assert called["dspy"] is False
    assert resume_analyzer._use_dspy_backend() is False


async def test_resume_analyzer_default_backend_is_dspy(monkeypatch):
    """Without the env var the default backend is DSPy."""
    monkeypatch.delenv("RESUME_LLM_BACKEND", raising=False)
    from app.intelligence.resume_analyzer import _use_dspy_backend

    assert _use_dspy_backend() is True


def test_matcher_scores_coverage_and_probes():
    result = match_candidate_to_role(
        skills=["python", "postgresql", "docker"],
        job_role="Backend Engineer",
        required_competencies=["tech_core", "tech_db", "behav_communication"],
    )
    assert result["match_score"] > 0.5
    assert "tech_core" in result["competency_coverage"]
    assert "behav_communication" in result["gaps"]
    assert result["recommended_probes"]


async def test_candidate_intelligence_bundle():
    bundle = await build_candidate_intelligence(
        job_role="Backend Engineer",
        candidate_profile={"full_name": "Jane", "skills": ["python"], "strengths": ["python"]},
        use_llm=False,
    )
    assert set(bundle) == {"candidate_brain", "initial_hypotheses", "candidate_assessment"}
    assert bundle["candidate_brain"]["full_name"] == "Jane"
    assert bundle["initial_hypotheses"]
    assert all("probability" in h for h in bundle["initial_hypotheses"])
    assert bundle["candidate_assessment"]["match_score"] > 0


# ---------------------------------------------------------------------------
# facade + engine injection
# ---------------------------------------------------------------------------

async def test_facade_returns_full_bundle(stub_llm):
    stub_llm(response=BLUEPRINT_JSON)
    bundle = await build_interview_intelligence(
        job_role="Backend Engineer",
        candidate_profile={"full_name": "Jane", "skills": ["python"], "strengths": ["python"]},
        competency_taxonomy=COMPETENCY_TAXONOMY,
        required_competencies=[c["id"] for c in COMPETENCY_TAXONOMY[:4]],
        use_rag=False,
    )
    assert set(bundle) == {
        "company_brain",
        "interview_blueprint",
        "candidate_brain",
        "initial_hypotheses",
        "evidence_requirements",
        "candidate_assessment",
        "aura_brain",
    }
    assert bundle["interview_blueprint"]["source"] == "llm"

    # AURA V5: the pre-interview brain ships company DNA + role intelligence.
    aura = bundle["aura_brain"]
    assert aura["company_brain"]["engineering_philosophy"]
    assert aura["role_brain"]["critical_competencies"]
    assert aura["competency_graph"]["nodes"]
    assert all("missing_evidence" in h for h in (aura["hypotheses"] or []))
    assert "question_strategy" in aura


async def test_facade_offline_without_llm_or_rag():
    bundle = await build_interview_intelligence(
        job_role="Backend Engineer",
        candidate_profile={"full_name": "Jane", "skills": ["python"], "strengths": ["python"]},
        use_rag=False,
        use_llm=False,
    )
    assert bundle["interview_blueprint"]["source"] == "fallback"
    assert bundle["candidate_brain"]["source"] in ("profile", "heuristics")
    assert bundle["aura_brain"]["role_brain"]["mission"]


async def test_engine_injects_intelligence_bundle(stub_llm, tmp_path):
    stub_llm(responses=[BLUEPRINT_JSON, STRATEGY_JSON, "Question: First question?"])
    store = MemoryV4SessionStore(db_path=str(tmp_path / "sessions.json"))

    engine = InterviewEngine(store=store)
    state = make_v4_state(
        session_id="intel-session-1",
        candidate_profile={"full_name": "Jane", "skills": ["python"], "strengths": ["python"]},
        resume_text="",
    )
    response = await engine.start_session(state, build_intelligence=True)

    assert response["status"] == "in_progress"
    assert response["question"]["text"]

    saved = store.get("intel-session-1")
    assert saved["company_brain"] is not None
    assert saved["interview_blueprint"]["source"] == "llm"
    assert saved["candidate_brain"]["full_name"] == "Jane"
    assert saved["initial_hypotheses"]
    assert saved["evidence_requirements"]
    assert saved["candidate_assessment"]["match_score"] > 0


async def test_engine_does_not_build_intelligence_by_default(stub_llm, tmp_path):
    stub_llm(responses=[STRATEGY_JSON, "Question: First question?"])
    store = MemoryV4SessionStore(db_path=str(tmp_path / "sessions.json"))

    engine = InterviewEngine(store=store)
    response = await engine.start_session(make_v4_state(session_id="plain-session-1"))

    assert response["status"] == "in_progress"
    assert response["question"]["text"]
    saved = store.get("plain-session-1")
    assert saved.get("company_brain") is None
    assert saved.get("candidate_brain") is None


# ---------------------------------------------------------------------------
# persist_intelligence_bundle — actual bundle key mapping (Phase 3)
# ---------------------------------------------------------------------------


class _FakeScalar:
    def __init__(self, row=None):
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class _FakeBundleSession:
    """AsyncSession stand-in: records adds, never finds rows, commits."""

    def __init__(self):
        self.added = []

    def add(self, record):
        self.added.append(record)

    async def execute(self, statement):
        return _FakeScalar(None)

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def close(self):
        return None


async def test_persist_intelligence_bundle_maps_actual_bundle_keys():
    session_id = "11111111-1111-1111-1111-111111111111"
    bundle = {
        "company_brain": {
            "mission": "ship fast",
            "tech_stack": ["python"],
            "culture": ["blameless"],
            "documents_analyzed": ["resume.txt"],
        },
        "interview_blueprint": {
            "phases": ["intro", "technical"],
            "priority_competencies": [{"id": "tech_core", "name": "Core", "weight": 2.0}],
        },
        "candidate_brain": {
            "headline": "10y backend engineer",
            "skills": ["python"],
            "strengths": ["x"],
            "weaknesses": ["y"],
            "experience": [{"role": "SDE", "duration": "5 years"}],
        },
        "evidence_requirements": [
            {
                "competency": "tech_core",
                "name": "Core",
                "min_evidence": 2,
                "dimensions": ["technical"],
                "weight": 1.0,
                "verification_probe": "Ask about X",
            }
        ],
    }
    fake = _FakeBundleSession()

    saved = await persist_intelligence_bundle(
        session_id, department_id=None, job_role="Backend", bundle=bundle, db=fake
    )

    assert all(saved.values()), saved
    rows = {type(r): r for r in fake.added}

    company = rows[CompanyBrainRecord]
    assert company.company_vision == "ship fast"
    assert company.technical_stack == ["python"]
    assert company.source_documents == ["resume.txt"]
    assert company.snapshot == bundle["company_brain"]

    blueprint = rows[BlueprintRecord]
    assert blueprint.objectives == [{"competency": "tech_core", "name": "Core", "weight": 2.0}]
    assert blueprint.hypothesis_template == [
        {"competency": "tech_core", "statement": "Candidate demonstrates Core"}
    ]
    assert blueprint.snapshot == bundle["interview_blueprint"]

    scorecard = rows[ScorecardRecord]
    assert scorecard.competencies == [{"id": "tech_core", "name": "Core", "weight": 1.0}]
    assert scorecard.snapshot == bundle["interview_blueprint"]

    candidate = rows[CandidateBrainRecord]
    assert candidate.resume_summary == "10y backend engineer"
    assert candidate.work_history == bundle["candidate_brain"]["experience"]
    assert candidate.inferred_seniority == "mid"
    assert candidate.snapshot == bundle["candidate_brain"]

    requirement = rows[RequirementRecord]
    assert requirement.required_probes == ["Ask about X"]
    assert requirement.dimension == "technical"
    assert requirement.snapshot == bundle["evidence_requirements"][0]
