"""Cross-module contract tests: knowledge-base modules must interoperate.

These are pure (no DB, no LLM) and pin the stable contracts the T1/T2 waves
must not break. Importing anything here triggers module-level import of
app.brain.* and app.agents.* — both are proven import-safe by the existing
suite (e.g. tests/test_competency_consistency.py).
"""
import pytest

from app.data.competency_graph import COMPETENCY_GRAPH, competency_children, taxonomy_to_graph
from app.data.competency_resolver import default_taxonomy
from app.data.competency_taxonomy import (
    COMPETENCY_IDS,
    COMPETENCY_TAXONOMY,
    NON_IT_COMPETENCY_IDS,
    get_competency,
    map_skill_to_competency,
)

pytestmark = pytest.mark.contract


def test_default_taxonomy_applies_fallback_weights():
    taxonomy = default_taxonomy()
    # IT-only product: the default taxonomy never offers a sales/marketing/HR/finance competency
    assert {c["id"] for c in taxonomy} == set(COMPETENCY_IDS) - NON_IT_COMPETENCY_IDS
    assert not NON_IT_COMPETENCY_IDS & {c["id"] for c in taxonomy}
    by_id = {c["id"]: c for c in taxonomy}
    assert by_id["tech_core"]["weight"] == 3.0
    for comp in taxonomy:
        assert comp["max_score"] == 10.0
        assert comp["weight"] >= 1.0


def test_graph_covers_all_taxonomy_competencies():
    node_ids = set(COMPETENCY_GRAPH["nodes"])
    assert set(COMPETENCY_IDS) <= node_ids


def test_graph_children_are_knowledge_nodes():
    for child in competency_children("tech_db"):
        assert child in COMPETENCY_GRAPH["nodes"]


def test_taxonomy_to_graph_preserves_required_and_stubs_unknown():
    taxonomy = default_taxonomy()
    required = ["tech_core", "tech_db", "tech_data_modeling"]
    graph = taxonomy_to_graph(taxonomy, required_ids=required)
    for comp_id in required:
        node = graph["nodes"][comp_id]
        assert node["scope"] == "required"
    assert graph["nodes"]["tech_data_modeling"]["scope"] == "required"


def test_taxonomy_to_graph_keeps_children_for_known_competencies():
    taxonomy = default_taxonomy()
    graph = taxonomy_to_graph(taxonomy, required_ids=["tech_db"])
    assert "indexing" in graph["nodes"]
    assert "transactions" in graph["nodes"]


def test_unknown_competency_in_graph_degrades_to_stub():
    taxonomy = default_taxonomy()
    graph = taxonomy_to_graph(taxonomy, required_ids=["com_marketing_strategy"])
    node = graph["nodes"]["com_marketing_strategy"]
    assert node["type"] == "competency"
    assert node["category"] == "scope"
    assert node["scope"] == "required"


def test_map_skill_defaults_to_tech_core():
    assert map_skill_to_competency("python") == "tech_core"
    assert map_skill_to_competency("totally-unknown-skill") == "tech_core"


def test_get_competency_returns_empty_for_unknown():
    assert get_competency("nope") == {}
    assert get_competency("tech_core")["name"] == "Core Language Proficiency"
