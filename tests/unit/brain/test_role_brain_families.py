"""T1 (AURA-1.1) — role-brain family awareness for non-engineering jobs."""
import pytest

from app.brain.role_brain import (
    _CANONICAL_IMPORTANCE,
    build_role_brain,
    default_probe_for,
    detect_role_class,
)
from app.data.competency_resolver import default_taxonomy

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("Sales Director", "sales"),
        ("Marketing Manager", "marketing"),
        ("Product Designer", "design"),
        ("Product Manager", "product"),
        ("HR Business Partner", "hr"),
        ("Financial Analyst", "finance"),
        ("Operations Manager", "operations"),
        ("Customer Success Manager", "customer_success"),
        ("Backend Engineer", "backend"),
    ],
)
def test_detect_role_class_families(role, expected):
    assert detect_role_class(role)[0] == expected


def _family_taxonomy(category):
    return [
        c for c in default_taxonomy()
        if c["category"] in (category, "behavioral", "cognitive", "experience")
    ]


def test_build_role_brain_for_marketing():
    brain = build_role_brain(
        job_role="Marketing Manager",
        taxonomy=_family_taxonomy("marketing"),
        required_competencies=["mkt_brand_strategy", "mkt_campaign_management"],
    )
    assert brain["class"] == "marketing"
    assert brain["source"] == "knowledge_base"
    ids = [c["id"] for c in brain["critical_competencies"]]
    assert "mkt_brand_strategy" in ids
    for comp in brain["critical_competencies"]:
        assert 1 <= comp["importance"] <= 10
        assert comp["must_prove"]


def test_build_role_brain_for_finance():
    brain = build_role_brain(
        job_role="Financial Analyst",
        taxonomy=_family_taxonomy("finance"),
        required_competencies=["fin_financial_analysis"],
    )
    assert brain["class"] == "finance"
    by_id = {c["id"]: c for c in brain["critical_competencies"]}
    assert by_id["fin_financial_analysis"]["importance"] >= _CANONICAL_IMPORTANCE[
        "fin_financial_analysis"
    ]


def test_customer_success_importance_band():
    brain = build_role_brain(
        job_role="Customer Success Manager",
        taxonomy=_family_taxonomy("customer_success"),
        required_competencies=["cs_churn_retention", "cs_account_management"],
    )
    by_id = {c["id"]: c for c in brain["critical_competencies"]}
    assert by_id["cs_churn_retention"]["importance"] >= 7
    assert by_id["cs_account_management"]["importance"] >= 7


def test_family_probes_are_specific():
    probes = {
        "com_sales_strategy": "revenue",
        "mkt_brand_strategy": "positioning",
        "prd_product_strategy": "strategy",
        "fin_financial_analysis": "financial model",
        "ops_process_improvement": "process",
        "cs_churn_retention": "churn",
    }
    for comp_id, fragment in probes.items():
        probe = default_probe_for(comp_id)
        assert probe and probe != "Walk me through a concrete example from your experience."


def test_generic_probe_fallback_for_unlisted_family_comp():
    assert default_probe_for("mkt_seo_ppc")  # non-empty even when unlisted
