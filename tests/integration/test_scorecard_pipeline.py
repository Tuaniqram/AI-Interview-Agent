"""DB-backed scorecard pipeline test.

Creates a small organization/session with a custom scorecard, writes evidence,
runs the finalize persistence, and checks that:

  * a ``saturated`` hypothesis persists (the old check constraint rejected it),
  * the session accepts the ``summary`` phase,
  * a weighted ``scorecard_results`` row is written with the linked template.

Run with a real database:

    PYTEST_USE_DB=1 pytest -m integration tests/integration/test_scorecard_pipeline.py

It self-skips when no database is configured.
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from app.auth.password import hash_password
from app.core.interview_brain import InterviewBrain
from app.database.session import get_session_factory
from app.models.db import (
    Competency,
    EvidenceStore,
    Hypothesis,
    InterviewSession,
    InterviewTemplate,
    ItRole,
    Organization,
    RoleCompetency,
    ScorecardResult,
    ScorecardTemplate,
    User,
)
from app.services.v5_brain_persister import V5BrainPersister

pytestmark = [pytest.mark.integration, pytest.mark.db]


async def test_finalize_persists_saturated_hypothesis_and_custom_scorecard(live_db):
    factory = get_session_factory()
    created = {}
    async with factory() as db:
        role = (await db.execute(select(ItRole).order_by(ItRole.name).limit(1))).scalar_one_or_none()
        if role is None:
            pytest.skip("IT catalog is empty")

        comp_rows = (await db.execute(
            select(RoleCompetency, Competency)
            .join(Competency, Competency.id == RoleCompetency.competency_id)
            .where(RoleCompetency.role_id == role.id)
            .limit(3)
        )).all()
        if not comp_rows:
            pytest.skip("role has no catalog competencies")

        now = datetime.now(timezone.utc)
        user = User(
            id=uuid.uuid4(),
            email=f"scorecard-test-{uuid.uuid4().hex}@example.com",
            password_hash=hash_password("Test123!"),
            name="Scorecard Test Owner",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        org = Organization(
            id=uuid.uuid4(),
            owner_user_id=user.id,
            name="Scorecard Test Org",
            slug=f"scorecard-test-{uuid.uuid4().hex}",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(org)
        await db.flush()

        competencies = [
            {
                "id": comp.id,
                "name": comp.name,
                "category": comp.category or "general",
                "weight": float(rc.weight or 1.0),
                "max_score": 10.0,
            }
            for rc, comp in comp_rows
        ]

        scorecard = ScorecardTemplate(
            id=uuid.uuid4(),
            org_id=org.id,
            name="Pipeline Test Scorecard",
            competencies=competencies,
        )
        db.add(scorecard)
        await db.flush()

        template = InterviewTemplate(
            id=uuid.uuid4(),
            org_id=org.id,
            it_role_id=role.id,
            name="Pipeline Test Template",
            job_role_snapshot=role.name,
            interview_style="AURA",
            total_questions=14,
            competencies=competencies,
            scorecard_template_id=scorecard.id,
        )
        db.add(template)
        await db.flush()

        session = InterviewSession(
            id=uuid.uuid4(),
            org_id=org.id,
            it_role_id=role.id,
            job_role_snapshot=role.name,
            session_type="public",
            interaction_mode="typing",
            engine_version="v5",
            status="completed",
            current_phase="summary",
            scorecard_template_id=scorecard.id,
            template_id=template.id,
            ended_at=now,
        )
        db.add(session)
        await db.flush()

        for index, comp in enumerate(competencies):
            db.add(EvidenceStore(
                id=uuid.uuid4(),
                session_id=session.id,
                competency_id=comp["id"],
                dimension="technical",
                score=8.0 - index,
                confidence=0.9,
                evidence_text=f"Evidence for {comp['name']}",
                source_question="Test question",
                question_number=index + 1,
            ))
        await db.commit()
        created = {"org": org.id, "user": user.id}

    brain = InterviewBrain(session_id=str(session.id))
    brain.evaluation_score = 7.0
    brain.competency_summary = {
        comp["id"]: {"average_score": 8.0 - i, "evidence_count": 1}
        for i, comp in enumerate(competencies)
    }
    brain.competency_taxonomy = competencies
    brain.hypotheses = [{
        "id": str(uuid.uuid4()),
        "competency": competencies[0]["id"],
        "statement": "Candidate demonstrates the core competency",
        "direction": "positive",
        "confidence": 0.5,
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "status": "saturated",
    }]

    try:
        await V5BrainPersister(session_factory=get_session_factory).save_relational(brain, finalize=True)

        async with factory() as db:
            hypothesis = (await db.execute(
                select(Hypothesis).where(Hypothesis.session_id == session.id)
            )).scalar_one()
            assert hypothesis.status == "saturated"

            result = (await db.execute(
                select(ScorecardResult).where(ScorecardResult.session_id == session.id)
            )).scalar_one()
            assert result.template_id == scorecard.id
            assert result.weighted_score is not None
            assert set(result.scores.keys()) == {c["id"] for c in competencies}
            assert all("name" in entry for entry in result.scores.values())

            saved_session = await db.get(InterviewSession, session.id)
            assert saved_session.current_phase == "summary"
    finally:
        async with factory() as db:
            await db.execute(text("DELETE FROM organizations WHERE id = :id"), {"id": created["org"]})
            await db.execute(text("DELETE FROM users WHERE id = :id"), {"id": created["user"]})
            await db.commit()
