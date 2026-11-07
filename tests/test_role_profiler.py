"""F1-F6 role-first pipeline tests (targeted — only what changed)."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.decision.decision_engine import (
    HIRE_MIN_COVERAGE,
    STRONG_HIRE_MIN_COVERAGE,
    decide_hiring_decision,
)
from app.agents.generation.question_generator import (
    _fallback_question,
    phase_for_question,
)
from app.agents.reasoning.claim_validator import (
    generic_term_hits,
    quantified_claim_count,
    repeated_phrases,
    validate_answers,
)
from app.config.interview_styles import get_style
from app.data.competency_resolver import (
    default_taxonomy,
    is_thin_scorecard,
    resolve_competencies,
)
from app.intelligence.role_competency_profiler import (
    build_role_context,
    role_cache_key,
    suggest_competencies,
    _validate_suggestions,
)

# --------------------------------------------------------------------------- #
# F1 — RoleProfiler validation & deterministic fallback
# --------------------------------------------------------------------------- #

VALID_SUGGESTION = {
    "competencies": [
        {
            "id": "tech_frontend",
            "name": "Frontend Architecture & React",
            "category": "technical",
            "evidence_dimensions": ["technical", "reasoning"],
            "weight": 3.0,
            "default_min_evidence": 2,
            "verification_probe": "Walk me through your last component architecture trade-off.",
            "skills": ["react", "typescript", "frontend"],
        },
        {
            "id": "behav_stakeholder_mgmt",
            "name": "Stakeholder Communication",
            "category": "behavioral",
            "evidence_dimensions": ["communication", "behavioral"],
            "weight": 2.0,
            "default_min_evidence": 2,
            "verification_probe": "How did you align stakeholders on a hard deadline?",
            "skills": ["stakeholders", "communication"],
        },
        {
            "id": "cog_product_thinking",
            "name": "Product Thinking",
            "category": "cognitive",
            "evidence_dimensions": ["reasoning", "completeness"],
            "weight": 2.0,
            "default_min_evidence": 1,
            "verification_probe": "Walk through a product decision you reversed.",
            "skills": ["product", "prioritization"],
        },
        {
            "id": "exp_ui_delivery",
            "name": "UI Delivery at Scale",
            "category": "experience",
            "evidence_dimensions": ["technical", "completeness"],
            "weight": 1.5,
            "default_min_evidence": 2,
            "verification_probe": "Show a launch you shipped end to end.",
            "skills": ["launch", "delivery"],
        },
    ],
    "rationale": "Frontend roles live or die on architecture, stakeholders and delivery.",
}


def test_suggestions_validated_keep_good_entries():
    entries, rationale = _validate_suggestions(VALID_SUGGESTION)
    assert len(entries) == 4
    assert entries[0]["id"] == "tech_frontend"
    assert entries[0]["weight"] == 3.0
    assert entries[0]["evidence_dimensions"] == ["technical", "reasoning"]
    assert entries[0]["skills"] == ["react", "typescript", "frontend"]
    assert rationale


def test_suggestions_drop_invalid_ids_and_categories():
    payload = dict(VALID_SUGGESTION)
    payload["competencies"] = [
        dict(VALID_SUGGESTION["competencies"][0], id="FrontEnd!"),
        dict(VALID_SUGGESTION["competencies"][0], id="no_prefix"),
        dict(VALID_SUGGESTION["competencies"][0], id="tech_good", category="madeup"),
        *VALID_SUGGESTION["competencies"][1:],
    ]
    entries, _ = _validate_suggestions(payload)
    ids = [e["id"] for e in entries]
    assert "tech_frontend" not in ids
    assert "no_prefix" not in ids
    assert "tech_good" in ids
    assert len(entries) == 4


def test_suggestions_cap_at_six_and_dedupe():
    payload = dict(VALID_SUGGESTION)
    payload["competencies"] = [
        *VALID_SUGGESTION["competencies"],
        dict(VALID_SUGGESTION["competencies"][0], id="tech_extra1", name="Extra 1"),
        dict(VALID_SUGGESTION["competencies"][0], id="tech_extra2", name="Extra 2"),
        dict(VALID_SUGGESTION["competencies"][0], id="tech_extra3", name="Extra 3"),
        dict(VALID_SUGGESTION["competencies"][0], id="tech_frontend", name="Dup"),
    ]
    entries, _ = _validate_suggestions(payload)
    assert len(entries) == 6
    assert len({e["id"] for e in entries}) == 6


def test_deterministic_fallback_never_empty():
    ctx = build_role_context(
        job_role="Senior Backend Engineer",
        skills_required=["Python", "FastAPI", "PostgreSQL", "Kafka"],
    )
    entries, source, _ = asyncio.run(suggest_competencies(ctx, use_llm=False))
    assert source == "ai:deterministic"
    assert len(entries) >= 4
    assert all(e["id"] for e in entries)
    assert all(e["verification_probe"] for e in entries)


def test_deterministic_fallback_reacts_to_role():
    backend = build_role_context(
        job_role="Senior Backend Engineer",
        skills_required=["Python", "FastAPI", "PostgreSQL", "Kafka", "Redis", "AWS"],
    )
    frontend = build_role_context(
        job_role="Senior Frontend Engineer",
        skills_required=["React", "TypeScript", "CSS", "Accessibility", "Design Systems"],
    )
    b_entries, _, _ = asyncio.run(suggest_competencies(backend, use_llm=False))
    f_entries, _, _ = asyncio.run(suggest_competencies(frontend, use_llm=False))
    b_ids = {e["id"] for e in b_entries}
    f_ids = {e["id"] for e in f_entries}
    assert "tech_framework" in b_ids
    assert "tech_db" in b_ids
    assert "tech_devops" in b_ids
    assert "tech_framework" in f_ids
    assert b_ids != f_ids


def test_role_cache_key_stable_and_distinct():
    a = build_role_context(job_role="Senior Backend Engineer", skills_required=["Python"])
    b = build_role_context(job_role="Senior Backend Engineer", skills_required=["Python"])
    c = build_role_context(job_role="Senior Frontend Engineer", skills_required=["Python"])
    assert role_cache_key(a) == role_cache_key(b)
    assert role_cache_key(a) != role_cache_key(c)


def test_thin_scorecard_rule():
    assert is_thin_scorecard([{"id": "a"}] * 3) is True
    assert is_thin_scorecard([{"id": "a"}] * 4) is False
    assert is_thin_scorecard([]) is False
    assert is_thin_scorecard(None) is False


# --------------------------------------------------------------------------- #
# F1 — resolution order (scorecard -> template -> AI -> default)
# --------------------------------------------------------------------------- #

SIX = [{"id": f"tech_c{i}", "name": f"Comp {i}"} for i in range(6)]
THREE = [{"id": f"tech_c{i}", "name": f"Comp {i}"} for i in range(3)]
SCORECARD_UUID = "90f31c8f-b4ed-4a0a-9568-8c8eee2511b4"


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeResult:
    def __init__(self, rows=None, single=None):
        self._rows = rows or []
        self._single = single

    def scalar_one_or_none(self):
        return self._single

    def scalars(self):
        return _Rows(self._rows)


class FakeDB:
    def __init__(self, scorecard: list | None = None, template: list | None = None):
        self._scorecard = scorecard
        self._template = template

    async def execute(self, stmt):
        statement = str(stmt)
        if "scorecard_templates" in statement:
            single = None
            if self._scorecard is not None:
                single = type("T", (), {"competencies": self._scorecard})()
            return FakeResult(single=single)
        if "interview_templates" in statement:
            rows = []
            if self._template is not None:
                rows = [type("T", (), {"competencies": self._template, "id": "tpl"})]
            return FakeResult(rows=rows)
        return FakeResult()


async def _resolve(*, scorecard=None, template=None, role_context=None, use_llm=True):
    with patch("app.data.competency_resolver._db_suggestion_cache", AsyncMock(return_value=[])), \
         patch("app.data.competency_resolver._persist_suggestion", AsyncMock()):
        db = FakeDB(scorecard=scorecard, template=template)
        return await resolve_competencies(
            db,
            scorecard_template_id=SCORECARD_UUID if scorecard is not None else None,
            org_id="7" if template is not None or role_context else None,
            role_context=role_context,
            use_llm=use_llm,
        )


def test_full_scorecard_wins():
    entries = asyncio.run(_resolve(scorecard=SIX, template=THREE))
    assert len(entries) == 6


def test_thin_scorecard_triggers_ai_pass():
    ctx = build_role_context(job_role="Senior Backend Engineer", skills_required=["Python"])
    entries = asyncio.run(_resolve(scorecard=THREE, template=None, role_context=ctx))
    # AI deterministic pass fires (LLM stubbed off) and outranks the thin rubric.
    assert len(entries) >= 4
    assert all(e["id"].startswith(("tech_", "behav_", "cog_", "exp_")) for e in entries)


def test_template_wins_over_ai_when_complete():
    ctx = build_role_context(job_role="Senior Backend Engineer", skills_required=["Python"])
    entries = asyncio.run(_resolve(scorecard=None, template=SIX, role_context=ctx))
    assert len(entries) == 6


def test_default_taxonomy_without_role_context():
    entries = asyncio.run(_resolve(scorecard=None, template=None, role_context=None))
    assert entries == default_taxonomy()


def test_resolution_cached_in_memory():
    from app.data.competency_resolver import _RESOLUTION_CACHE

    _RESOLUTION_CACHE.clear()
    ctx = build_role_context(job_role="Senior Backend Engineer", skills_required=["Python"])
    with patch("app.data.competency_resolver._db_suggestion_cache", AsyncMock(return_value=[])) as dbc, \
         patch("app.data.competency_resolver._persist_suggestion", AsyncMock()), \
         patch("app.data.competency_resolver.suggest_competencies", AsyncMock(
             return_value=([{"id": "tech_backend", "name": "Backend", "category": "technical",
                             "weight": 1.0, "evidence_dimensions": ["technical"],
                             "default_min_evidence": 2}], "ai:llm", "x"))) as sugg:
        db = FakeDB()
        asyncio.run(resolve_competencies(db, org_id="7", role_context=ctx))
        assert sugg.await_count == 1
        asyncio.run(resolve_competencies(db, org_id="7", role_context=ctx))
        assert sugg.await_count == 1  # second resolve hits the memory cache
        assert dbc.await_count == 1


# --------------------------------------------------------------------------- #
# F2 — fallback question bank (no verbatim duplicates)
# --------------------------------------------------------------------------- #

def test_fallback_bank_variants_differ():
    texts = [_fallback_question("communication", "Senior Frontend Engineer", 5, variant=i)
             for i in range(4)]
    assert len(set(texts)) == 4
    assert "trade-offs" in texts[0] or "senior-level" in texts[0]


def test_legacy_fallback_signature_unchanged():
    assert "senior-level" in _fallback_question("communication", "Engineer", 5)
    assert "senior-level" not in _fallback_question("communication", "Engineer", 3)


# --------------------------------------------------------------------------- #
# F3 — phase controller
# --------------------------------------------------------------------------- #

def test_phase_budgets_advance_for_aura():
    style = get_style("AURA")
    seq = [phase_for_question(i, style) for i in range(1, 15)]
    assert seq[:2] == ["intro", "intro"]
    assert seq[2:8] == ["technical"] * 6
    assert seq[8:13] == ["behavioral"] * 5
    assert seq[13:] == ["conclusion"]


def test_phase_budgets_respect_style_override():
    style = {"phase_order": ["intro", "technical", "conclusion"], "max_questions": 10,
             "phase_budgets": {"intro": 2, "technical": 7, "conclusion": 1}}
    assert phase_for_question(3, style) == "technical"
    assert phase_for_question(9, style) == "technical"
    assert phase_for_question(10, style) == "conclusion"
    assert phase_for_question(11, style) == "conclusion"


# --------------------------------------------------------------------------- #
# F4 — verdict caps
# --------------------------------------------------------------------------- #

def test_strong_hire_capped_on_low_coverage():
    result = decide_hiring_decision(
        holistic_score=9.6, coverage_ratio=0.73, confirmed_ratio=0.8,
        difficulty_reached=5, evidence_count=13,
    )
    assert result["decision"] == "hire"  # capped from strong_hire
    assert "strong_hire capped" in result["signals"]["coverage_capped"]
    assert result["flag_review"] is True


def test_hire_capped_on_very_low_coverage():
    result = decide_hiring_decision(
        holistic_score=8.0, coverage_ratio=0.6, confirmed_ratio=0.7,
        difficulty_reached=4, evidence_count=10,
    )
    assert result["decision"] == "lean_hire"


def test_strong_hire_survives_full_coverage():
    result = decide_hiring_decision(
        holistic_score=9.2, coverage_ratio=0.9, confirmed_ratio=0.8,
        difficulty_reached=5, evidence_count=15,
    )
    assert result["decision"] == "strong_hire"
    assert result["signals"]["coverage_capped"] == ""


# --------------------------------------------------------------------------- #
# F5 — claim validator
# --------------------------------------------------------------------------- #

def test_repeated_phrases_detected_across_answers():
    answers = [
        "I led the migration of the payments platform to a new stack and cut latency by 40 percent.",
        "I led the migration of the payments platform and improved throughput.",
        "Something else entirely about design systems and React.",
    ]
    repeated = repeated_phrases(answers)
    assert "led migration payments platform" in repeated


def test_generic_terms_and_quantification():
    answers = ["I'm a seasoned, passionate, hardworking engineer with a proven track record."]
    assert "seasoned" in generic_term_hits(answers)
    assert quantified_claim_count(answers) == 0
    answers2 = ["We cut p95 latency by 40% and saved $2m annually."]
    assert quantified_claim_count(answers2) == 1


def test_authenticity_score_penalizes_filler_rewards_numbers():
    filler = validate_answers(["I am a passionate dedicated team player."] * 3)
    quantified = validate_answers([
        "Cut p95 latency 40% with caching.",
        "Reduced error rate from 2% to 0.4%.",
        "Scaled to 10k concurrent users.",
    ])
    assert filler["authenticity_score"] < quantified["authenticity_score"]
    assert quantified["has_quantified_evidence"] is True


# --------------------------------------------------------------------------- #
# F6 — calibration quantification discipline
# --------------------------------------------------------------------------- #

def test_calibration_demands_quantification_for_85():
    from app.agents.evaluation.scoring import _apply_evaluator_calibration

    vague = {
        "technical": {"score": 9.0, "evidence": "Gave a strong example of an architecture decision"},
    }
    out = _apply_evaluator_calibration(vague)
    assert out["technical"]["score"] == 8.0  # example but no numbers -> 8 cap

    quantified = {
        "technical": {"score": 9.0, "evidence": "Example: cut latency 40% by owning the architecture"},
    }
    out2 = _apply_evaluator_calibration(quantified)
    assert out2["technical"]["score"] == 9.0  # example + numbers + ownership -> stands

    no_example = {"technical": {"score": 8.5, "evidence": "Seems solid"}}
    out3 = _apply_evaluator_calibration(no_example)
    assert out3["technical"]["score"] == 7.0


def test_aura_style_enables_calibration():
    style = get_style("AURA")
    assert style.get("apply_evaluator_calibration") is True
