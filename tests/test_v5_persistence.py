"""V5 persistence + reasoning-path regression tests.

Covers the Phase 1 V5 fixes:
  * ``V5BrainPersister`` maps an ``InterviewBrain`` into the interview_brain /
    evidence_graph / interview_timeline rows (and no-ops without a database).
  * The engine invokes ``save_snapshot`` at the V5 turn boundary.
  * ``conversation_turn`` survives brain sync and dict round-trips (A9).
  * Communication is reserved at the hypothesis cap with a 0.5 prior (A12).
  * ``update_hypotheses`` is a single Bayesian path where confidence mirrors
    probability (A11), evidence is applied once (A5), and intelligence-built
    ``initial_hypotheses`` reach the runtime path (hypothesis-node seeding).
"""
from uuid import UUID, uuid4

import pytest

from app.agents.reasoning.evidence_engine import evidence_extractor_node
from app.agents.reasoning.hypothesis_engine import (
    PRIOR_CONFIDENCE,
    generate_initial_hypotheses,
    update_hypotheses,
    hypothesis_node,
)
from app.core.interview_brain import InterviewBrain
from app.core.interview_state import brain_to_dict, dict_to_brain
from app.engine.engine import InterviewEngine
from app.models.db import (
    ConsistencyCheck as ConsistencyCheckRecord,
    EvidenceGraph as EvidenceGraphRecord,
    InterviewBrain as InterviewBrainRecord,
    InterviewTimeline as InterviewTimelineRecord,
    Observation as ObservationRecord,
    ScorecardResult as ScorecardResultRecord,
)
from app.services.v4_session_store import MemoryV4SessionStore
from app.services.v5_brain_persister import V5BrainPersister
from tests.conftest import (
    CONDUCTOR_TURN_JSON,
    EVALUATOR_JSON,
    GOVERNOR_JSON,
    STRATEGY_JSON,
    make_v4_state,
    refutable_hypotheses,
)


# --------------------------------------------------------------------- #
# V5BrainPersister unit tests
# --------------------------------------------------------------------- #


class _ScalarResult:
    def __init__(self, row=None):
        self._row = row

    def scalar_one_or_none(self):
        return self._row

    def scalars(self):
        return _ScalarRows(self._row)


class _ScalarRows:
    def __init__(self, row=None):
        self._row = row

    def first(self):
        return self._row


class _Namespace:
    """Attribute-assignable row stand-in (an ``object()`` cannot take attrs)."""

    def __init__(self):
        self.event_data = None


class FakeSession:
    """Async context-manager stand-in for an AsyncSession: records adds,
    optionally finds an existing row, commits silently."""

    def __init__(self, existing: bool = False):
        self.added = []
        self.existing = existing

    def add(self, record):
        self.added.append(record)

    async def execute(self, statement):
        return _ScalarResult(_Namespace()) if self.existing else _ScalarResult(None)

    async def commit(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSessionFactory:
    def __init__(self):
        self.session = FakeSession()

    def __call__(self):
        return self.session


def _make_brain() -> InterviewBrain:
    brain = InterviewBrain()
    brain.session_id = str(uuid4())
    brain.question_number = 2
    brain.current_phase = "technical"
    brain.difficulty_level = 2
    brain.difficulty_profile = {"level": 2, "dimensions": []}
    brain.hypotheses = [
        {"id": "h1", "competency": "tech_core", "status": "testing", "probability": 0.6}
    ]
    brain.competency_summary = {"tech_core": {"average_score": 8.0, "evidence_count": 1}}
    brain.evidence_graph = {
        "nodes": {"tech_core": {"type": "competency", "count": 1}},
        "edges": {"e1->h1": {"weight": 0.9, "support": True}},
    }
    brain.conversation_turn = {"acknowledgement": "ok", "bridge": "let me", "question": "next?"}
    brain.company_brain = {"source": "test"}
    brain.aura_brain = {"company_brain": {"source": "test"}, "question_strategy": {"action": "ask"}}
    brain.uncertainty_map = {"tech_core": {"uncertainty": 0.42}}
    brain.question_strategy = {"question_strategy": {"mode": "verify"}, "planned_competency": "tech_core"}
    brain.contradiction_state = {"needs_challenge": False}
    brain.calibration_state = {"calibrated_verdict": "hire"}
    brain.candidate_memory = {"prior_rounds": 1}
    brain.hiring_decision = {"decision": "hire", "decision_score": 8.2, "confidence": 0.7}
    brain.state_version = 3
    return brain


async def test_save_snapshot_writes_brain_graph_and_timeline_rows():
    factory = FakeSessionFactory()
    persister = V5BrainPersister(session_factory=lambda: factory)
    brain = _make_brain()

    await persister.save_snapshot(brain)

    added = factory.session.added
    assert len(added) == 3

    brain_rec = next(r for r in added if isinstance(r, InterviewBrainRecord))
    assert brain_rec.session_id == UUID(brain.session_id)
    assert brain_rec.version == brain.state_version + 1
    assert brain_rec.current_hypotheses == brain.hypotheses
    assert brain_rec.evidence_summary == brain.competency_summary
    assert brain_rec.competency_scores == brain.evidence_graph["nodes"]
    assert brain_rec.difficulty_profile == brain.difficulty_profile
    assert brain_rec.decision_state["reflection_action"] == brain.reflection_action
    assert brain_rec.decision_state["hiring_decision"] == brain.hiring_decision
    assert brain_rec.decision_state["hiring_decision"]["decision"] == "hire"
    assert brain_rec.brain_metadata["conversation_turn"] == brain.conversation_turn
    assert brain_rec.brain_metadata["company_brain"] == brain.company_brain
    assert brain_rec.brain_metadata["question_number"] == 2
    assert brain_rec.brain_metadata["aura_brain"] == brain.aura_brain
    assert brain_rec.brain_metadata["uncertainty_map"] == brain.uncertainty_map
    assert brain_rec.brain_metadata["question_strategy"] == brain.question_strategy
    assert brain_rec.brain_metadata["contradiction_state"] == brain.contradiction_state
    assert brain_rec.brain_metadata["calibration_state"] == brain.calibration_state
    assert brain_rec.brain_metadata["candidate_memory"] == brain.candidate_memory

    graph_rec = next(r for r in added if isinstance(r, EvidenceGraphRecord))
    assert graph_rec.session_id == UUID(brain.session_id)
    assert graph_rec.nodes == brain.evidence_graph["nodes"]
    assert graph_rec.edges == brain.evidence_graph["edges"]

    tl_rec = next(r for r in added if isinstance(r, InterviewTimelineRecord))
    assert tl_rec.session_id == UUID(brain.session_id)
    assert tl_rec.event_type == "brain_snapshot"
    assert tl_rec.question_number == 2
    assert tl_rec.event_data["version"] == brain.state_version + 1


async def test_save_snapshot_upserts_timeline_row_per_question():
    """B1 regression: the engine persists a snapshot after every turn *and* at
    finalize, so the same question must never produce two brain_snapshot rows
    (15 events / 14 questions). A second snapshot for the same question
    updates the existing row instead of appending a duplicate."""
    factory = FakeSessionFactory()
    persister = V5BrainPersister(session_factory=lambda: factory)
    brain = _make_brain()

    await persister.save_snapshot(brain)
    assert len(factory.session.added) == 3

    # Re-save the same question_number (finalize path) — must upsert, not add.
    factory.session.existing = True
    factory.session.added.clear()
    brain.state_version = 4
    await persister.save_snapshot(brain)

    assert len(factory.session.added) == 1
    (updated,) = factory.session.added
    assert updated.event_data["version"] == brain.state_version + 1


def test_backfill_evidence_summary_unions_zero_evidence_required_competencies():
    """Regression for the brain_view gap inconsistency: evidence_summary must
    include every required competency (zero-evidence ones with gap=1.0) so it
    matches evidence_sufficiency.details instead of silently dropping them."""
    from app.services.v5_brain_persister import _backfill_evidence_summary

    summary = {
        "tech_core": {"evidence_count": 3, "average_score": 8.0, "gap": 0.0},
    }
    out = _backfill_evidence_summary(
        summary, ["tech_core", "tech_deployment", "tech_data_modeling"]
    )
    assert set(out.keys()) == {"tech_core", "tech_deployment", "tech_data_modeling"}
    assert out["tech_core"] == summary["tech_core"]
    assert out["tech_deployment"] == {
        "evidence_count": 0,
        "average_score": 0.0,
        "average_confidence": 0.0,
        "average_strength": 0.0,
        "coverage": 0.0,
        "gap": 1.0,
    }
    assert out["tech_data_modeling"]["gap"] == 1.0
    assert out["tech_data_modeling"]["evidence_count"] == 0


async def test_save_snapshot_backfills_zero_evidence_required_competencies():
    factory = FakeSessionFactory()
    persister = V5BrainPersister(session_factory=lambda: factory)
    brain = _make_brain()
    brain.required_competencies = ["tech_core", "tech_deployment"]

    await persister.save_snapshot(brain)

    brain_rec = next(r for r in factory.session.added if isinstance(r, InterviewBrainRecord))
    assert brain_rec.evidence_summary["tech_core"]["average_score"] == 8.0
    assert brain_rec.evidence_summary["tech_deployment"] == {
        "evidence_count": 0,
        "average_score": 0.0,
        "average_confidence": 0.0,
        "average_strength": 0.0,
        "coverage": 0.0,
        "gap": 1.0,
    }


async def test_save_snapshot_noops_without_database():
    persister = V5BrainPersister(session_factory=lambda: None)
    await persister.save_snapshot(_make_brain())  # must not raise


async def test_save_snapshot_skips_invalid_session_id():
    factory = FakeSessionFactory()
    persister = V5BrainPersister(session_factory=lambda: factory)
    brain = _make_brain()
    brain.session_id = "not-a-uuid"

    await persister.save_snapshot(brain)

    assert factory.session.added == []


# --------------------------------------------------------------------- #
# Engine → persister wiring
# --------------------------------------------------------------------- #


class RecordingPersister:
    def __init__(self):
        self.snapshots = []

    async def save_snapshot(self, brain):
        self.snapshots.append(brain)


@pytest.fixture
def fake_store(tmp_path):
    return MemoryV4SessionStore(db_path=str(tmp_path / "sessions.json"))


async def test_engine_v5_answer_invokes_save_snapshot(
    fake_store, stub_llm, fake_evidence_repo, fake_repos
):
    stub_llm(
        responses=[
            STRATEGY_JSON,
            "Question: First question?",
            EVALUATOR_JSON,
            GOVERNOR_JSON,
            CONDUCTOR_TURN_JSON,
        ]
    )
    persister = RecordingPersister()
    engine = InterviewEngine(store=fake_store, v5_persister=persister)
    session_id = "persist-engine-1"
    state = make_v4_state(session_id=session_id, flow_type="v5_evidence_driven")

    await engine.start_session(state)
    response = await engine.process_answer(session_id, "I built distributed systems.")

    assert response["status"] == "in_progress"
    assert persister.snapshots
    snapshot = persister.snapshots[-1]
    assert snapshot.session_id == session_id
    assert snapshot.state_version >= 1
    assert snapshot.hypotheses, "hypotheses should be seeded by session start"


# --------------------------------------------------------------------- #
# Phase 3 — relational tables (observations / consistency checks /
# scorecard_results)
# --------------------------------------------------------------------- #


def _make_relational_brain() -> InterviewBrain:
    brain = InterviewBrain()
    brain.session_id = str(uuid4())
    brain.answered_question_numbers = [3]
    brain.question_number = 3
    brain.observations = [
        {"type": "hedging", "value": 0.7, "evidence": ""},
        {"type": "notable_patterns", "value": "frequently says 'um'"},
    ]
    brain.consistency_checks = [
        {
            "type": "cross_check",
            "assessment": "consistent",
            "score": 8.0,
            "confidence": 0.9,
            "evidence": "matches prior answer",
        }
    ]
    brain.competency_summary = {
        "tech_core": {"score": 8.0, "evidence_count": 1, "confidence": 0.85}
    }
    brain.evaluation_score = 7.5
    return brain


async def test_save_relational_enriches_observations():
    factory = FakeSessionFactory()
    persister = V5BrainPersister(session_factory=lambda: factory)

    await persister.save_relational(_make_relational_brain(), finalize=False)

    obs = [r for r in factory.session.added if isinstance(r, ObservationRecord)]
    assert len(obs) == 2
    by_type = {r.type: r for r in obs}
    assert by_type["hedging"].pattern == "hedging"
    assert by_type["hedging"].risk_signal == {"signal": "hedging"}
    assert by_type["hedging"].evidence == "hedging=0.70"
    assert by_type["notable_patterns"].pattern == "notable_patterns"
    assert by_type["notable_patterns"].risk_signal is None
    assert by_type["notable_patterns"].evidence == "frequently says 'um'"


async def test_save_relational_writes_mapped_consistency_check_columns():
    factory = FakeSessionFactory()
    persister = V5BrainPersister(session_factory=lambda: factory)

    await persister.save_relational(_make_relational_brain(), finalize=True)

    checks = [r for r in factory.session.added if isinstance(r, ConsistencyCheckRecord)]
    assert len(checks) == 1
    check = checks[0]
    assert check.check_type == "cross_check"
    assert check.assessment == "consistent"
    assert check.score == 8.0
    assert check.confidence == 0.9
    assert check.evidence == "matches prior answer"
    assert check.consistency_score == pytest.approx(0.72)


async def test_save_relational_writes_scorecard_result_on_finalize():
    factory = FakeSessionFactory()
    persister = V5BrainPersister(session_factory=lambda: factory)

    await persister.save_relational(_make_relational_brain(), finalize=True)

    results = [r for r in factory.session.added if isinstance(r, ScorecardResultRecord)]
    assert len(results) == 1
    result = results[0]
    assert result.scores == {
        "tech_core": {"score": 8.0, "evidence_count": 1, "confidence": 0.85}
    }
    assert result.weighted_score == 7.5


async def test_save_relational_skips_existing_finalize_rows():
    factory = FakeSessionFactory()
    factory.session = FakeSession(existing=True)
    persister = V5BrainPersister(session_factory=lambda: factory)

    await persister.save_relational(_make_relational_brain(), finalize=True)

    assert factory.session.added == []


async def test_save_relational_finalize_twice_does_not_duplicate_rows():
    factory = FakeSessionFactory()
    persister = V5BrainPersister(session_factory=lambda: factory)
    brain = _make_relational_brain()

    await persister.save_relational(brain, finalize=True)
    first_count = len(factory.session.added)
    await persister.save_relational(brain, finalize=True)
    second_count = len(factory.session.added)

    assert second_count == first_count
    scorecard_results = [r for r in factory.session.added if isinstance(r, ScorecardResultRecord)]
    assert len(scorecard_results) == 1


# --------------------------------------------------------------------- #
# A9 — conversation_turn survives sync / round-trip
# --------------------------------------------------------------------- #


def test_conversation_turn_survives_sync_from_dict():
    brain = InterviewBrain()
    turn = {"acknowledgement": "Got it.", "bridge": "Let me dig.", "question": "Go on?"}
    brain.sync_from_dict({"conversation_turn": turn})
    assert brain.conversation_turn == turn


def test_conversation_turn_preserved_through_dict_round_trip():
    brain = InterviewBrain(session_id="round-trip-1")
    turn = {"acknowledgement": "Got it.", "bridge": "Let me dig.", "question": "Go on?"}
    brain.conversation_turn = turn

    restored = dict_to_brain(brain_to_dict(brain))

    assert restored.conversation_turn == turn


# --------------------------------------------------------------------- #
# A12 — communication hypothesis is reserved at the cap, at the prior
# --------------------------------------------------------------------- #


def test_communication_hypothesis_starts_at_prior():
    hyps = generate_initial_hypotheses("Backend Engineer", max_hypotheses=1)
    assert len(hyps) == 1
    assert hyps[0]["competency"] == "behav_communication"
    assert hyps[0]["confidence"] == PRIOR_CONFIDENCE
    assert hyps[0]["probability"] == PRIOR_CONFIDENCE
    assert hyps[0]["status"] == "untested"


def test_communication_hypothesis_reserved_when_source_fills_cap():
    hyps = generate_initial_hypotheses(
        "Backend Engineer",
        candidate_profile={"strengths": ["a", "b", "c"], "weaknesses": ["x", "y", "z"]},
        max_hypotheses=6,
    )
    assert len(hyps) == 6
    assert any(h["competency"] == "behav_communication" for h in hyps)
    assert all(h["probability"] == PRIOR_CONFIDENCE for h in hyps)


# --------------------------------------------------------------------- #
# A11 / A5 — single Bayesian evidence path
# --------------------------------------------------------------------- #


def test_update_hypotheses_confidence_mirrors_probability():
    hyp = refutable_hypotheses(1)[0]
    hyp["confidence"] = PRIOR_CONFIDENCE
    hyp["probability"] = PRIOR_CONFIDENCE
    hyp["status"] = "untested"

    updated = update_hypotheses(
        [hyp],
        [{"id": "e1", "competency": "tech_core", "score": 8.0, "evidence_text": "x"}],
    )

    assert updated[0]["probability"] == pytest.approx(updated[0]["confidence"])
    assert updated[0]["probability"] != PRIOR_CONFIDENCE
    assert updated[0]["status"] == "testing"
    assert "e1" in updated[0]["supporting_evidence"]


async def test_evidence_extractor_does_not_apply_hypothesis_updates(fake_evidence_repo):
    hypotheses = refutable_hypotheses(1)
    state = make_v4_state(
        question_number=1,
        hypotheses=hypotheses,
        hypothesis_target=hypotheses[0],
        unified_evaluation={
            "technical": {"score": 8.0, "evidence": "strong", "confidence": 0.9,
                          "strengths": [], "weaknesses": []},
            "composite_score": 8.0,
        },
        evaluation_score=8.0,
    )

    result = await evidence_extractor_node(state)

    assert result["hypotheses"] == hypotheses
    assert result["hypotheses"][0]["status"] == "testing"
    assert result["extracted_evidence"]
    assert result["evidence_graph"]["nodes"]


async def test_hypothesis_node_seeds_from_initial_hypotheses(fake_evidence_repo):
    initial = [
        {
            "id": "ih1",
            "competency": "tech_core",
            "statement": "Candidate has strong tech_core skills",
            "direction": "positive",
            "confidence": PRIOR_CONFIDENCE,
            "probability": PRIOR_CONFIDENCE,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "status": "untested",
        }
    ]
    state = make_v4_state(
        session_id="seed-session",
        job_role="Software Engineer",
        hypotheses=[],
        initial_hypotheses=initial,
    )

    result = await hypothesis_node(state)

    assert result["hypotheses"] == [{
        **initial[0],
        "session_id": "seed-session",
        "required_evidence": 2,
        "max_allowed_evidence": 4,
        "evidence_count": 0,
    }]
    assert result["hypotheses"][0]["session_id"] == "seed-session"
    assert result["hypothesis_target"]["id"] == "ih1"
