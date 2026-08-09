"""T2 — family scoring rubrics (app/data/rubrics.py).

Pins the invariants the deterministic scoring layer relies on: every family
weights its ``domain`` dimension highest, non-tech families drop ``technical``
to zero, weights sum to one after overrides, and the F6 calibration keywords
are family-aware.
"""
import pytest

from app.data.rubrics import (
    FAMILY_WEIGHTS,
    active_dimensions,
    anchors,
    category_from_taxonomy,
    dimension_weights,
    domain_label_for,
    evidence_keywords,
    normalize_category,
    ownership_words,
    render_rubric,
)

pytestmark = pytest.mark.unit

NON_TECH_FAMILIES = {
    "commerce",
    "marketing",
    "design",
    "product",
    "hr",
    "finance",
    "operations",
    "customer_success",
}

META_CATEGORIES = {"behavioral", "cognitive", "experience"}


def test_tech_weights_keep_technical_primary():
    weights = dimension_weights("technical")
    assert weights["technical"] == 0.30
    assert weights.get("domain", 0.0) == 0.0
    assert sum(weights.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("family", sorted(NON_TECH_FAMILIES))
def test_non_tech_families_are_domain_first(family):
    weights = dimension_weights(family)
    assert weights["domain"] > 0, f"{family} must weight domain"
    assert weights["domain"] == max(weights.values()), f"{family} domain must be primary"
    assert weights.get("technical", 0.0) == 0.0, f"{family} must not score technical"


@pytest.mark.parametrize("family", sorted(META_CATEGORIES))
def test_meta_categories_keep_their_primary_dimension(family):
    weights = dimension_weights(family)
    assert sum(weights.values()) == pytest.approx(1.0), family
    primary = {
        "behavioral": "behavioral",
        "cognitive": "reasoning",
        "experience": "domain",
    }[family]
    assert weights[primary] == max(weights.values()), family


def test_every_family_weights_sum_to_one():
    for key in FAMILY_WEIGHTS:
        assert sum(dimension_weights(key).values()) == pytest.approx(1.0), key


def test_dimension_weights_merge_overrides_and_renormalize():
    weights = dimension_weights("marketing", {"domain": 0.5, "communication": 0.5})
    assert weights["domain"] > dimension_weights("marketing")["domain"]
    assert weights["domain"] > weights["technical"]
    assert sum(weights.values()) == pytest.approx(1.0)


def test_active_dimensions_exclude_zero_weight_dimensions():
    marketing = active_dimensions("marketing")
    assert "domain" in marketing
    assert "technical" not in marketing
    tech = active_dimensions("technical")
    assert "technical" in tech
    assert "domain" not in tech


def test_normalize_category_maps_aliases_and_prefixes():
    assert normalize_category("mkt_") == "marketing"
    assert normalize_category("Marketing") == "marketing"
    assert normalize_category("com_anything") == "commerce"
    assert normalize_category(None) == "technical"
    assert normalize_category("unknown") == "technical"


def test_category_from_taxonomy_resolves_target():
    taxonomy = [{"id": "mkt_brand", "category": "marketing"}]
    assert category_from_taxonomy(taxonomy, "mkt_brand") == "marketing"
    assert category_from_taxonomy(taxonomy, "missing") is None
    assert category_from_taxonomy([], "mkt_brand") is None


def test_evidence_and_ownership_keywords_are_family_aware():
    assert "campaign" in evidence_keywords("marketing")
    assert "deal" in evidence_keywords("commerce")
    assert "churn" in evidence_keywords("customer_success")
    assert "churn" not in evidence_keywords("technical")
    assert "launched" in ownership_words("marketing")


def test_domain_label_for_family():
    assert domain_label_for("marketing") == "Marketing & Growth"
    assert domain_label_for("technical") == "Technical Knowledge"
    assert domain_label_for(None) == "Technical Knowledge"


def test_anchors_cover_only_scored_dimensions():
    for dim in anchors("marketing"):
        assert dimension_weights("marketing").get(dim, 0.0) > 0


def test_render_rubric_includes_family_label_and_weights():
    rendered = render_rubric("marketing")
    assert "Marketing & Growth" in rendered
    assert "domain (30% weight)" in rendered
