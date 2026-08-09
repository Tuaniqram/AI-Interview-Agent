"""T1 (AURA-1.1) — job-family taxonomy expansion.

Covers the 8 new job families (commerce, marketing, design, product, hr,
finance, operations, customer_success) plus the four re-added tech
competencies. These tests pin the invariants the canary enforces at the
family level and drive the deterministic, offline profiler.
"""
import asyncio

import pytest

from app.data.competency_graph import COMPETENCY_CHILDREN
from app.data.competency_resolver import DEFAULT_DIMENSIONS_BY_CATEGORY, derive_domain_label
from app.data.competency_taxonomy import (
    COMPETENCY_CATEGORIES,
    COMPETENCY_IDS,
    COMPETENCY_TAXONOMY,
)
from app.intelligence.role_competency_profiler import (
    _validate_suggestions,
    build_role_context,
    detect_family,
    suggest_competencies,
)

pytestmark = pytest.mark.unit

FAMILIES = {
    "commerce": "com_",
    "marketing": "mkt_",
    "design": "des_",
    "product": "prd_",
    "hr": "hr_",
    "finance": "fin_",
    "operations": "ops_",
    "customer_success": "cs_",
}

TECH_ORPHANS = {
    "tech_event_driven",
    "tech_deployment",
    "tech_caching",
    "tech_data_modeling",
}


@pytest.mark.parametrize("family,prefix", FAMILIES.items())
def test_every_family_has_at_least_four_competencies(family, prefix):
    ids = [c["id"] for c in COMPETENCY_TAXONOMY if c["category"] == family]
    assert len(ids) >= 4, f"{family} has only {len(ids)} competencies"
    assert all(i.startswith(prefix) for i in ids), f"{family} ids must use {prefix}"


def test_family_categories_registered():
    for family in FAMILIES:
        assert family in COMPETENCY_CATEGORIES


def test_tech_orphans_are_restored_to_taxonomy():
    assert TECH_ORPHANS <= set(COMPETENCY_IDS)


def test_graph_parents_now_all_in_taxonomy():
    missing = set(COMPETENCY_CHILDREN) - set(COMPETENCY_IDS)
    assert not missing, f"orphaned graph parents remain: {missing}"


def test_non_tech_competencies_lead_with_domain_dimension():
    families = set(FAMILIES)
    non_tech = [c for c in COMPETENCY_TAXONOMY if c["category"] in families]
    assert non_tech
    for c in non_tech:
        assert "domain" in c["evidence_dimensions"], f"{c['id']} must use the domain dimension"


def test_every_new_competency_has_min_evidence():
    new_ids = set(COMPETENCY_IDS) - set(
        ["tech_core", "tech_framework", "tech_system_design", "tech_data", "tech_db",
         "tech_devops", "tech_testing", "tech_security", "behav_teamwork",
         "behav_leadership", "behav_conflict", "behav_communication",
         "behav_adaptability", "cog_problem_solving", "cog_analytical",
         "cog_creativity", "cog_decision_making", "exp_project_depth", "exp_domain",
         "exp_scaling", "exp_best_practices"]
    )
    for c in COMPETENCY_TAXONOMY:
        if c["id"] in new_ids:
            assert c.get("default_min_evidence"), f"{c['id']} missing default_min_evidence"


def test_all_dimension_defaults_exist_for_new_categories():
    for family in FAMILIES:
        assert family in DEFAULT_DIMENSIONS_BY_CATEGORY


def test_domain_label_for_non_tech_taxonomy():
    marketing_taxonomy = [
        c for c in COMPETENCY_TAXONOMY if c["category"] in ("marketing", "customer_success")
    ]
    assert derive_domain_label(marketing_taxonomy) == "Domain Knowledge"


def test_domain_label_still_technical_when_tech_present():
    tech_taxonomy = [c for c in COMPETENCY_TAXONOMY if c["category"] == "technical"]
    assert derive_domain_label(tech_taxonomy) == "Technical Knowledge"


# --------------------------------------------------------------------------- #
# Deterministic profiler — family-aware (offline)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    ("role", "expected_family"),
    [
        ("Marketing Manager", "marketing"),
        ("Sales Director", "commerce"),
        ("Product Manager", "product"),
        ("UX Designer", "design"),
        ("HR Business Partner", "hr"),
        ("Financial Analyst", "finance"),
        ("Operations Manager", "operations"),
        ("Customer Success Manager", "customer_success"),
        ("Senior Backend Engineer", "technical"),
    ],
)
def test_detect_family_from_title(role, expected_family):
    assert detect_family(role, "") == expected_family


@pytest.mark.parametrize(
    ("role", "skills", "prefix"),
    [
        ("Marketing Manager", ["SEO", "Content Strategy", "Email Marketing"], "mkt_"),
        ("Sales Director", ["B2B Sales", "Pipeline Management"], "com_"),
        ("Product Manager", ["Roadmap", "User Stories"], "prd_"),
        ("UX Designer", ["Figma", "User Research", "Prototyping"], "des_"),
        ("HR Business Partner", ["Recruiting", "Employee Relations"], "hr_"),
        ("Financial Analyst", ["Financial Modeling", "Forecasting"], "fin_"),
        ("Operations Manager", ["Supply Chain", "Process Improvement"], "ops_"),
        ("Customer Success Manager", ["Retention", "Renewals"], "cs_"),
    ],
)
def test_deterministic_profiler_returns_family_competencies(role, skills, prefix):
    ctx = build_role_context(job_role=role, skills_required=skills)
    entries, source, _ = asyncio.run(suggest_competencies(ctx, use_llm=False))
    assert source == "ai:deterministic"
    assert len(entries) >= 4
    family_ids = [e["id"] for e in entries if e["id"].startswith(prefix)]
    assert family_ids, f"{role} produced no {prefix} competencies: {[e['id'] for e in entries]}"
    for e in entries:
        assert e["verification_probe"], f"{e['id']} missing probe"


def test_deterministic_profiler_never_empty_for_unknown_role():
    ctx = build_role_context(job_role="Purple Widget Specialist", skills_required=["wobbling"])
    entries, source, _ = asyncio.run(suggest_competencies(ctx, use_llm=False))
    assert source == "ai:deterministic"
    assert len(entries) >= 4


# --------------------------------------------------------------------------- #
# LLM-pass validation accepts the new families
# --------------------------------------------------------------------------- #

FAMILY_SUGGESTIONS = {
    "competencies": [
        {
            "id": "mkt_brand_strategy",
            "name": "Brand Strategy",
            "category": "marketing",
            "evidence_dimensions": ["domain", "reasoning"],
            "weight": 3.0,
            "default_min_evidence": 2,
            "verification_probe": "Walk me through a positioning decision.",
            "skills": ["brand", "positioning"],
        },
        {
            "id": "com_negotiation",
            "name": "Deal Negotiation",
            "category": "commerce",
            "evidence_dimensions": ["domain", "communication"],
            "weight": 2.0,
            "default_min_evidence": 2,
            "verification_probe": "Tell me about your hardest deal.",
            "skills": ["negotiation", "closing"],
        },
        {
            "id": "fin_financial_analysis",
            "name": "Financial Analysis",
            "category": "finance",
            "evidence_dimensions": ["domain", "reasoning"],
            "weight": 2.0,
            "default_min_evidence": 2,
            "verification_probe": "Show me a model you built.",
            "skills": ["modeling", "forecasting"],
        },
        {
            "id": "cs_churn_retention",
            "name": "Churn Prevention",
            "category": "customer_success",
            "evidence_dimensions": ["domain", "reasoning"],
            "weight": 2.0,
            "default_min_evidence": 1,
            "verification_probe": "Show me a churn turnaround.",
            "skills": ["churn", "retention"],
        },
        {
            "id": "prd_product_strategy",
            "name": "Product Strategy",
            "category": "product",
            "evidence_dimensions": ["domain", "reasoning"],
            "weight": 3.0,
            "default_min_evidence": 2,
            "verification_probe": "Walk me through a strategy you owned.",
            "skills": ["roadmap", "vision"],
        },
        {
            "id": "des_visual_design",
            "name": "Visual Design",
            "category": "design",
            "evidence_dimensions": ["domain", "communication"],
            "weight": 2.0,
            "default_min_evidence": 1,
            "verification_probe": "Show me a design tradeoff.",
            "skills": ["ui", "figma"],
        },
    ],
    "rationale": "Family roles need family competencies.",
}


def test_llm_validation_accepts_family_competencies():
    entries, rationale = _validate_suggestions(FAMILY_SUGGESTIONS)
    ids = {e["id"] for e in entries}
    assert ids == {
        "mkt_brand_strategy",
        "com_negotiation",
        "fin_financial_analysis",
        "cs_churn_retention",
        "prd_product_strategy",
        "des_visual_design",
    }
    assert rationale
    cats = {e["category"] for e in entries}
    assert cats == {"marketing", "commerce", "finance", "customer_success", "product", "design"}


def test_llm_validation_still_rejects_invalid_prefix():
    payload = dict(FAMILY_SUGGESTIONS)
    payload["competencies"] = [
        dict(FAMILY_SUGGESTIONS["competencies"][0], id="sales_strategy", name="No Prefix"),
        FAMILY_SUGGESTIONS["competencies"][0],
        *FAMILY_SUGGESTIONS["competencies"][1:],
    ]
    entries, _ = _validate_suggestions(payload)
    ids = {e["id"] for e in entries}
    assert "sales_strategy" not in ids  # invalid prefix dropped
    assert "mkt_brand_strategy" in ids  # valid family id kept


def test_llm_validation_coerces_unknown_category_to_general():
    payload = dict(FAMILY_SUGGESTIONS)
    payload["competencies"] = [
        dict(FAMILY_SUGGESTIONS["competencies"][0], category="madeup"),
        *FAMILY_SUGGESTIONS["competencies"][1:],
    ]
    entries, _ = _validate_suggestions(payload)
    by_id = {e["id"]: e for e in entries}
    assert by_id["mkt_brand_strategy"]["category"] == "general"
