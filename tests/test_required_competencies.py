"""V5 required-competency focus (Fix 6): HIGH/MEDIUM subset capped at 6,
planner rotates only within the required set."""
from tests.conftest import COMPETENCY_TAXONOMY, make_v4_state

from app.agents.planning.competency_planner import plan_competencies
from app.data.competency_resolver import (
    MAX_REQUIRED_COMPETENCIES,
    derive_required_competencies,
    taxonomy_for_state,
)

PRIORITY = {
    "tech_core": "HIGH",
    "tech_framework": "HIGH",
    "tech_db": "MEDIUM",
    "tech_testing": "MEDIUM",
    "behav_communication": "MEDIUM",
    "cog_problem_solving": "HIGH",
}


def test_required_subset_prefers_high_then_medium():
    required = derive_required_competencies(COMPETENCY_TAXONOMY, PRIORITY)
    assert required[0] == "tech_core"
    assert required[1] == "tech_framework"
    assert required[2] == "cog_problem_solving"
    assert required[3] == "tech_db"
    assert "LOW_PRIORITY_COMP" not in required


def test_required_subset_capped_at_six():
    big_priority = {c["id"]: "HIGH" for c in COMPETENCY_TAXONOMY}
    required = derive_required_competencies(COMPETENCY_TAXONOMY, big_priority)
    assert len(required) == MAX_REQUIRED_COMPETENCIES


def test_required_subset_falls_back_to_first_six_without_priorities():
    required = derive_required_competencies(COMPETENCY_TAXONOMY, {})
    assert len(required) == MAX_REQUIRED_COMPETENCIES
    assert required == [c["id"] for c in COMPETENCY_TAXONOMY][:MAX_REQUIRED_COMPETENCIES]


def test_taxonomy_for_state_uses_priority_map():
    taxonomy, required, label = taxonomy_for_state(COMPETENCY_TAXONOMY, PRIORITY)
    assert required == derive_required_competencies(COMPETENCY_TAXONOMY, PRIORITY)
    assert len(required) <= MAX_REQUIRED_COMPETENCIES
    assert label == "Technical Knowledge"


def test_role_resolved_taxonomy_is_fully_required():
    """V5 role-first: a focused AI-profiled/scorecard taxonomy (<=6 entries)
    must NOT be shrunk by the generic priority map — every entry is required,
    so coverage can never be 100% after a single probed competency."""
    role_taxonomy = [
        {"id": "tech_system_design", "name": "System Design & Scalability", "category": "technical", "weight": 1.0},
        {"id": "tech_deployment", "name": "Reliable Deployments & AWS", "category": "technical", "weight": 1.0},
        {"id": "tech_event_driven", "name": "Event-Driven Processing", "category": "technical", "weight": 1.0},
        {"id": "tech_data_modeling", "name": "PostgreSQL Modeling", "category": "technical", "weight": 1.0},
        {"id": "tech_caching", "name": "Caching & Redis", "category": "technical", "weight": 1.0},
    ]
    priority_map = {"tech_system_design": "MEDIUM", "tech_core": "HIGH"}  # generic-map noise
    required = derive_required_competencies(role_taxonomy, priority_map)
    assert required == [c["id"] for c in role_taxonomy]
    _, required_state, _ = taxonomy_for_state(role_taxonomy, priority_map)
    assert len(required_state) == 5


async def test_planner_only_plans_required_competencies():
    required = derive_required_competencies(COMPETENCY_TAXONOMY, PRIORITY)
    state = make_v4_state(required_competencies=required)
    plan = plan_competencies(state)
    assert plan
    assert all(c["id"] in required for c in plan)
    assert len(plan) <= MAX_REQUIRED_COMPETENCIES


async def test_planner_full_taxonomy_when_required_unset():
    state = make_v4_state(required_competencies=[])
    plan = plan_competencies(state)
    assert plan
    assert len(plan) == len(COMPETENCY_TAXONOMY)


async def test_planner_sorts_high_priority_first():
    state = make_v4_state(
        required_competencies=["tech_core", "behav_communication"],
        interview_style={
            "base_competency_priority": {
                "tech_core": "HIGH",
                "behav_communication": "MEDIUM",
            }
        },
    )
    plan = plan_competencies(state)
    assert [c["id"] for c in plan] == ["tech_core", "behav_communication"]
