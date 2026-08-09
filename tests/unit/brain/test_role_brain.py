"""Role-brain determinism — the knowledge-base role layer must be pure,
repeatable, and safe to run offline (no LLM, no DB)."""
import pytest

from app.brain.role_brain import (
    _CANONICAL_IMPORTANCE,
    build_role_brain,
    classify_seniority,
    default_probe_for,
    detect_role_class,
)
from app.data.competency_resolver import default_taxonomy

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("Principal Engineer", "staff"),
        ("Staff Engineer", "staff"),
        ("Tech Lead", "staff"),
        ("Senior Backend Engineer", "senior"),
        ("Sr. Frontend Developer", "senior"),
        ("Junior Developer", "junior"),
        ("Entry Level Data Analyst", "junior"),
        ("Intern", "junior"),
        ("Mid-level Fullstack Engineer", "mid"),
        ("Software Engineer", "senior"),
    ],
)
def test_classify_seniority(role, expected):
    assert classify_seniority(role) == expected


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("Backend Engineer", "backend"),
        ("React Frontend Developer", "frontend"),
        ("Fullstack Engineer", "fullstack"),
        ("ML Engineer", "ml"),
        ("Data Engineer", "data"),
        ("DevOps Engineer", "devops"),
        ("iOS Developer", "mobile"),
        ("Sales Director", "sales"),
        ("Marketing Manager", "marketing"),
        ("Financial Analyst", "finance"),
        ("Backend Engineer", "backend"),
    ],
)
def test_detect_role_class(role, expected):
    assert detect_role_class(role)[0] == expected


def test_build_role_brain_is_deterministic():
    taxonomy = default_taxonomy()
    kwargs = {
        "job_role": "Senior Backend Engineer",
        "taxonomy": taxonomy,
        "required_competencies": ["tech_core", "tech_db", "cog_problem_solving"],
    }
    first = build_role_brain(**kwargs)
    second = build_role_brain(**kwargs)
    assert first == second


def test_build_role_brain_shapes():
    brain = build_role_brain(
        job_role="Senior Backend Engineer",
        taxonomy=default_taxonomy(),
        required_competencies=["tech_core", "tech_db", "cog_problem_solving"],
    )
    assert brain["source"] == "knowledge_base"
    assert brain["seniority_floor"] == 3
    assert brain["critical_competencies"], "must produce critical competencies"
    for comp in brain["critical_competencies"]:
        assert 1 <= comp["importance"] <= 10
        assert comp["must_prove"], f"{comp['id']} missing must_prove"


def test_importance_lives_in_1_10_band():
    taxonomy = default_taxonomy()
    brain = build_role_brain(job_role="Backend Engineer", taxonomy=taxonomy)
    importances = [c["importance"] for c in brain["critical_competencies"]]
    assert min(importances) >= 1
    assert max(importances) <= 10


def test_default_probe_never_empty():
    for comp_id in _CANONICAL_IMPORTANCE:
        assert default_probe_for(comp_id), f"no probe for {comp_id}"
    assert default_probe_for("unknown_competency")
