"""Taxonomy integrity canary — the single most important guard in the suite.

Every competency id referenced anywhere in the engine's knowledge bases must
exist in the canonical taxonomy, and every taxonomy entry must be well-formed.
This file is the tripwire for the "Interview Any Job" expansion
([AURA-1.1][T1-taxonomy]) and any future family additions.

KNOWN_GAP: the competency graph and the role-brain importance map reference four
tech competencies that are absent from the taxonomy (the "orphans"):
tech_event_driven, tech_deployment, tech_caching, tech_data_modeling.
The assertions below allow exactly those four to be missing until T1 re-adds
them — they start green, stay green through T1, and will fail if any OTHER
referenced id is ever missing.
"""
import pytest

from app.brain.role_brain import _CANONICAL_IMPORTANCE
from app.data.competency_graph import COMPETENCY_CHILDREN
from app.data.competency_resolver import CANONICAL_DIMENSIONS, DEFAULT_DIMENSIONS_BY_CATEGORY, _FALLBACK_WEIGHTS
from app.data.competency_taxonomy import (
    COMPETENCY_CATEGORIES,
    COMPETENCY_IDS,
    COMPETENCY_TAXONOMY,
    SKILL_TO_COMPETENCY,
)

KNOWN_ORPHANS = {
    "tech_event_driven",
    "tech_deployment",
    "tech_caching",
    "tech_data_modeling",
}

pytestmark = pytest.mark.unit


def test_taxonomy_ids_are_unique():
    assert len(COMPETENCY_IDS) == len(set(COMPETENCY_IDS)), "duplicate competency ids"


def test_every_category_is_a_known_category():
    unknown = {c["category"] for c in COMPETENCY_TAXONOMY} - set(COMPETENCY_CATEGORIES)
    assert not unknown, f"unknown categories: {unknown}"


def test_every_evidence_dimension_is_canonical():
    unknown = {
        dim
        for c in COMPETENCY_TAXONOMY
        for dim in c.get("evidence_dimensions", [])
    } - CANONICAL_DIMENSIONS
    assert not unknown, f"unknown evidence dimensions: {unknown}"


def test_skill_map_only_targets_taxonomy_ids():
    unknown = set(SKILL_TO_COMPETENCY.values()) - set(COMPETENCY_IDS)
    assert not unknown, f"skills map to unknown competencies: {unknown}"


def test_default_dimension_map_keys_are_known_categories():
    unknown = set(DEFAULT_DIMENSIONS_BY_CATEGORY) - set(COMPETENCY_CATEGORIES)
    assert not unknown, f"unknown categories in DEFAULT_DIMENSIONS_BY_CATEGORY: {unknown}"


def test_default_dimension_map_dims_are_canonical():
    unknown = {
        dim
        for dims in DEFAULT_DIMENSIONS_BY_CATEGORY.values()
        for dim in dims
    } - CANONICAL_DIMENSIONS
    assert not unknown, f"unknown dimensions in DEFAULT_DIMENSIONS_BY_CATEGORY: {unknown}"


def test_fallback_weights_only_target_taxonomy_ids():
    unknown = set(_FALLBACK_WEIGHTS) - set(COMPETENCY_IDS)
    assert not unknown, f"fallback weights reference unknown competencies: {unknown}"


def test_graph_parents_only_missing_known_orphans():
    missing = set(COMPETENCY_CHILDREN) - set(COMPETENCY_IDS)
    unexpected = missing - KNOWN_ORPHANS
    assert not unexpected, f"graph parents missing from taxonomy: {unexpected}"


def test_role_importance_only_missing_known_orphans():
    missing = set(_CANONICAL_IMPORTANCE) - set(COMPETENCY_IDS)
    unexpected = missing - KNOWN_ORPHANS
    assert not unexpected, f"role importance keys missing from taxonomy: {unexpected}"


def test_known_orphans_are_documented_in_graph():
    assert KNOWN_ORPHANS <= set(COMPETENCY_CHILDREN), "documented orphans vanished from graph"


def test_every_taxonomy_entry_has_min_evidence():
    missing = [c["id"] for c in COMPETENCY_TAXONOMY if not c.get("default_min_evidence")]
    assert not missing, f"competencies missing default_min_evidence: {missing}"
