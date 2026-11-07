"""The engine interviews on the IT catalog: every catalog competency is known to the engine, the
product never offers a non-IT competency, and the resolver ranks an IT role's own competencies
above the AI profiler (scorecard -> org template -> IT catalog -> AI profiler -> default)."""
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.data import competency_resolver as resolver
from app.data.competency_resolver import default_taxonomy, resolve_competencies, taxonomy_for_state
from app.data.competency_taxonomy import (
    COMPETENCY_IDS,
    NON_IT_COMPETENCY_IDS,
    SKILL_TO_COMPETENCY,
    map_skill_to_competency,
)

SEED = Path(__file__).resolve().parents[1] / "docs" / "it-scope" / "seed-it-catalog.sql"


def _seed_sql() -> str:
    if not SEED.exists():
        pytest.skip("IT catalog seed not present")
    return SEED.read_text(encoding="utf-8")


def _catalog_competency_ids() -> set[str]:
    sql = _seed_sql()
    block = sql[sql.index("INSERT INTO competencies"):]
    block = block[: block.index(";")]
    return set(re.findall(r"\('([a-z_]+)',\s*'(?:[^']|'')*',\s*'[a-z_]+',\s*'[a-z_]+',\s*ARRAY", block))


def _role_family_competency_ids() -> set[str]:
    sql = _seed_sql()
    block = sql[sql.index("INSERT INTO role_competencies"):]
    block = block[: block.index(";")]
    return set(re.findall(r"\('[a-z_]+',\s*'([a-z_]+)',\s*[\d.]+,", block))


# ── alignment with the seeded catalog ────────────────────────────────────


def test_every_catalog_competency_is_known_to_the_engine():
    catalog = _catalog_competency_ids()
    assert len(catalog) == 60
    assert catalog <= set(COMPETENCY_IDS), f"engine is missing: {sorted(catalog - set(COMPETENCY_IDS))}"


def test_every_competency_a_role_uses_is_known_to_the_engine():
    used = _role_family_competency_ids()
    assert used, "seed parsing found no role competencies"
    assert used <= set(COMPETENCY_IDS), f"unknown to the engine: {sorted(used - set(COMPETENCY_IDS))}"


def test_non_it_competencies_are_not_in_the_catalog_or_any_role():
    assert not NON_IT_COMPETENCY_IDS & _catalog_competency_ids()
    assert not NON_IT_COMPETENCY_IDS & _role_family_competency_ids()


# ── IT-only defaults and skills ──────────────────────────────────────────


def test_default_taxonomy_offers_no_non_it_competency():
    ids = {c["id"] for c in default_taxonomy()}
    assert not ids & NON_IT_COMPETENCY_IDS
    assert _catalog_competency_ids() <= ids  # ...and offers the whole IT catalog


def test_no_skill_maps_to_a_non_it_competency():
    assert not set(SKILL_TO_COMPETENCY.values()) & NON_IT_COMPETENCY_IDS


@pytest.mark.parametrize("skill,competency", [
    ("terraform", "tech_iac"),
    ("jenkins", "tech_ci_cd"),
    ("google cloud", "tech_cloud"),
    ("pytorch", "tech_ml"),
    ("kotlin", "tech_mobile"),
    ("prometheus", "tech_monitoring"),
    ("salesforce", "tech_erp_crm"),
    ("python", "tech_core"),  # existing mappings are untouched
])
def test_it_skills_map_onto_catalog_competencies(skill, competency):
    assert map_skill_to_competency(skill) == competency


# ── resolver order ───────────────────────────────────────────────────────

ROLE_ID = "11111111-1111-1111-1111-111111111111"
SIX = [{"id": f"tech_c{i}", "name": f"C{i}", "category": "technical", "weight": 1.0,
        "evidence_dimensions": ["technical"], "default_min_evidence": 2} for i in range(6)]


def _row(cid, name, category, weight, core, dims=("technical", "completeness"), min_ev=2):
    rc = SimpleNamespace(weight=weight, is_core=core)
    comp = SimpleNamespace(id=cid, name=name, category=category, evidence_dimensions=list(dims), default_min_evidence=min_ev)
    return rc, comp


class FakeDB:
    def __init__(self, catalog_rows):
        self.catalog_rows = catalog_rows
        self.catalog_queries = 0

    async def execute(self, stmt):
        assert "role_competencies" in str(stmt), "only the catalog query should reach the DB in these tests"
        self.catalog_queries += 1
        rows = self.catalog_rows
        return SimpleNamespace(all=lambda: rows)


def _patched(scorecard=None, template=None, ai=None):
    return (
        patch.object(resolver, "_resolve_scorecard_defs", AsyncMock(return_value=scorecard or [])),
        patch.object(resolver, "_resolve_template_defs", AsyncMock(return_value=(template or [], None))),
        patch.object(resolver, "_ai_pass", AsyncMock(return_value=ai or [])),
    )


async def test_it_role_catalog_drives_the_taxonomy_and_skips_the_ai_profiler():
    rows = [_row("tech_ci_cd", "CI/CD", "technical", 3.0, True), _row("tech_iac", "IaC", "technical", 2.0, True)]
    db = FakeDB(rows)
    p1, p2, p3 = _patched()
    with p1, p2, p3 as ai_pass:
        taxonomy = await resolve_competencies(db, it_role_id=ROLE_ID, role_context={"job_role": "DevOps"})
    assert [c["id"] for c in taxonomy] == ["tech_ci_cd", "tech_iac"]
    assert taxonomy[0]["weight"] == 3.0 and taxonomy[0]["max_score"] == 10.0
    assert taxonomy[0]["evidence_dimensions"] == ["technical", "completeness"]
    ai_pass.assert_not_called()  # a catalog role never needs an LLM call to pick its competencies


async def test_a_complete_org_scorecard_still_outranks_the_catalog():
    db = FakeDB([_row("tech_ci_cd", "CI/CD", "technical", 3.0, True)])
    p1, p2, p3 = _patched(scorecard=SIX)
    with p1, p2, p3:
        taxonomy = await resolve_competencies(db, scorecard_template_id="sc", it_role_id=ROLE_ID)
    assert [c["id"] for c in taxonomy] == [c["id"] for c in SIX]
    assert db.catalog_queries == 0


async def test_a_complete_org_template_outranks_the_catalog():
    db = FakeDB([_row("tech_ci_cd", "CI/CD", "technical", 3.0, True)])
    p1, p2, p3 = _patched(template=SIX)
    with p1, p2, p3:
        taxonomy = await resolve_competencies(db, org_id="7", it_role_id=ROLE_ID)
    assert [c["id"] for c in taxonomy] == [c["id"] for c in SIX]
    assert db.catalog_queries == 0


async def test_role_without_catalog_competencies_falls_through_to_the_ai_profiler():
    ai_entries = [{"id": "tech_core", "name": "Core", "category": "technical", "weight": 1.0, "max_score": 10.0,
                   "evidence_dimensions": ["technical"], "default_min_evidence": 2}]
    db = FakeDB([])
    p1, p2, p3 = _patched(ai=ai_entries)
    with p1, p2, p3:
        taxonomy = await resolve_competencies(db, it_role_id=ROLE_ID, role_context={"job_role": "X"})
    assert taxonomy == ai_entries


async def test_no_role_id_means_no_catalog_query_and_the_it_default():
    db = FakeDB([_row("tech_ci_cd", "CI/CD", "technical", 3.0, True)])
    p1, p2, p3 = _patched()
    with p1, p2, p3:
        taxonomy = await resolve_competencies(db)
    assert taxonomy == default_taxonomy()
    assert db.catalog_queries == 0


async def test_catalog_taxonomy_feeds_the_engine_state_and_respects_the_cap():
    rows = [_row(f"tech_c{i}", f"C{i}", "technical", 1.0, i < 4) for i in range(6)]
    p1, p2, p3 = _patched()
    with p1, p2, p3:
        taxonomy = await resolve_competencies(FakeDB(rows), it_role_id=ROLE_ID)
    competency_taxonomy, required, _label = taxonomy_for_state(taxonomy)
    assert len(competency_taxonomy) == 6
    assert 1 <= len(required) <= 6  # MAX_REQUIRED_COMPETENCIES
    assert set(required) <= {c["id"] for c in competency_taxonomy}


async def test_invalid_dimensions_in_the_catalog_are_sanitized():
    rows = [_row("tech_x", "X", "technical", 1.0, True, dims=("technical", "not_a_dimension"))]
    p1, p2, p3 = _patched()
    with p1, p2, p3:
        taxonomy = await resolve_competencies(FakeDB(rows), it_role_id=ROLE_ID)
    assert taxonomy[0]["evidence_dimensions"] == ["technical"]


# ── the deterministic role matcher ───────────────────────────────────────


def test_common_title_words_do_not_match_inside_multi_word_skills():
    from app.intelligence.role_competency_profiler import _suggest_from_taxonomy, build_role_context

    ctx = build_role_context(job_role="Senior Backend Engineer", skills_required=["Python"])
    ids = [e["id"] for e in _suggest_from_taxonomy(ctx)]
    assert "tech_llm" not in ids  # "engineer" is a substring of "prompt engineering"
    assert "tech_core" in ids


def test_llm_role_still_matches_llm_competency():
    from app.intelligence.role_competency_profiler import _suggest_from_taxonomy, build_role_context

    ctx = build_role_context(job_role="Prompt Engineer", skills_required=["LangChain", "RAG"])
    assert "tech_llm" in [e["id"] for e in _suggest_from_taxonomy(ctx)]
