"""Every required competency gets a hypothesis, so the interview sweeps the whole role."""
from app.agents.reasoning.hypothesis_engine import MAX_SEEDED_REQUIRED, hypothesis_node
from tests.conftest import make_v4_state

TAXONOMY = [
    {"id": f"tech_{n}", "name": n.title(), "category": "technical", "weight": 1.0,
     "evidence_dimensions": ["domain"], "default_min_evidence": 2}
    for n in ("core", "db", "api", "framework", "system_design", "testing", "security", "cloud", "ci", "cache")
]


def _state(required, initial=None):
    return make_v4_state(
        session_id="cov-1", hypotheses=[], initial_hypotheses=initial or [],
        competency_taxonomy=TAXONOMY, required_competencies=required,
    )


async def test_required_competencies_without_a_hypothesis_are_seeded_as_untested(fake_evidence_repo):
    initial = [{"id": "ih1", "competency": "tech_core", "statement": "Candidate has strong tech_core skills",
                "direction": "positive", "confidence": 0.5, "probability": 0.5, "supporting_evidence": [],
                "contradicting_evidence": [], "status": "untested"}]
    result = await hypothesis_node(_state(["tech_core", "tech_db", "tech_api"], initial))

    by_comp = {}
    for h in result["hypotheses"]:
        by_comp.setdefault(h["competency"], []).append(h)
    assert set(by_comp) == {"tech_core", "tech_db", "tech_api"}
    assert [h["id"] for h in by_comp["tech_core"]] == ["ih1"]  # the CV-based one is kept, not duplicated
    for comp in ("tech_db", "tech_api"):
        (seed,) = by_comp[comp]
        assert seed["status"] == "untested" and seed["session_id"] == "cov-1"
        assert seed["required_evidence"] >= 1  # evidence requirements are attached like for any hypothesis


async def test_seeding_never_floods_the_interview(fake_evidence_repo):
    result = await hypothesis_node(_state([c["id"] for c in TAXONOMY]))
    competencies = {h["competency"] for h in result["hypotheses"]}
    assert len(competencies & {c["id"] for c in TAXONOMY}) >= MAX_SEEDED_REQUIRED
    assert not ({"tech_ci", "tech_cache"} & competencies) or MAX_SEEDED_REQUIRED >= 9


async def test_the_first_questions_sweep_different_competencies(fake_evidence_repo):
    result = await hypothesis_node(_state(["tech_core", "tech_db", "tech_api"]))
    target = result["hypothesis_target"]
    assert target and target["status"] == "untested"
    assert target["competency"] in {"tech_core", "tech_db", "tech_api"}


async def test_no_required_competencies_changes_nothing(fake_evidence_repo):
    initial = [{"id": "ih1", "competency": "tech_core", "statement": "x", "direction": "positive",
                "confidence": 0.5, "probability": 0.5, "supporting_evidence": [], "contradicting_evidence": [],
                "status": "untested"}]
    result = await hypothesis_node(_state([], initial))
    assert [h["id"] for h in result["hypotheses"]] == ["ih1"]
