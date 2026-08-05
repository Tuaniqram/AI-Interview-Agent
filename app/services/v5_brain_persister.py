"""V5 brain persistence — the durable snapshot of the interview reasoning state.

Writes the three V5 tables (``interview_brain``, ``evidence_graph``,
``interview_timeline``) after every V5 turn and on finalize. It is the concrete
implementation of the engine's opt-in ``v5_persister`` seam: pass an instance to
``InterviewEngine(v5_persister=...)`` and the engine calls ``save_snapshot(brain)``
at the turn boundary. Failures are non-fatal by design (persistence must never
break an interview), and the session factory can be injected for tests.
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from app.database.session import get_session_factory
from app.models.db import (
    EvidenceGraph as EvidenceGraphRecord,
    InterviewBrain as InterviewBrainRecord,
    InterviewTimeline as InterviewTimelineRecord,
)

logger = logging.getLogger(__name__)


class V5BrainPersister:
    """Upsert the V5 reasoning snapshot for a session."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or get_session_factory

    async def save_snapshot(self, brain) -> None:
        """Persist one brain snapshot (brain + evidence graph + timeline row).

        ``brain`` is an ``InterviewBrain`` (or anything exposing the same
        attributes). No-ops silently when persistence is unavailable.
        """
        session_id_str = getattr(brain, "session_id", "")
        if not session_id_str:
            return
        try:
            session_id = UUID(session_id_str)
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Invalid session_id for v5 snapshot: {session_id_str!r}")
            return

        factory = self._session_factory()
        if factory is None:
            logger.debug("v5 persister no-op: DATABASE_URL not configured")
            return

        async with factory() as session:
            await self._upsert_brain(session, session_id, brain)
            await self._upsert_graph(session, session_id, brain)
            await self._append_timeline(session, session_id, brain)
            await session.commit()

    # ------------------------------------------------------------------ #

    async def _upsert_brain(self, session, session_id: UUID, brain) -> None:
        result = await session.execute(
            select(InterviewBrainRecord).where(
                InterviewBrainRecord.session_id == session_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = InterviewBrainRecord(session_id=session_id)
            session.add(record)

        record.version = int(getattr(brain, "state_version", 0) or 0) + 1
        record.current_hypotheses = getattr(brain, "hypotheses", []) or []
        record.evidence_summary = getattr(brain, "competency_summary", {}) or {}
        nodes = (getattr(brain, "evidence_graph", {}) or {}).get("nodes", {}) or {}
        record.competency_scores = nodes
        record.difficulty_profile = getattr(brain, "difficulty_profile", None)
        record.decision_state = {
            "reflection_action": getattr(brain, "reflection_action", None),
            "director": getattr(brain, "director", {}) or {},
            "consecutive_probes": int(getattr(brain, "consecutive_probes", 0) or 0),
            "hiring_recommendation": getattr(brain, "hiring_recommendation", {}) or {},
            "evidence_sufficiency": getattr(brain, "evidence_sufficiency", {}) or {},
            "contradictions": getattr(brain, "contradictions", []) or [],
            "consistency_checks": getattr(brain, "consistency_checks", []) or [],
        }
        record.brain_metadata = {
            "flow_type": getattr(brain, "flow_type", None),
            "current_phase": getattr(brain, "current_phase", None),
            "question_number": getattr(brain, "question_number", 0),
            "question_objective": getattr(brain, "question_objective", None),
            "conversation_turn": getattr(brain, "conversation_turn", None),
            "company_brain": getattr(brain, "company_brain", None),
            "interview_blueprint": getattr(brain, "interview_blueprint", None),
            "candidate_brain": getattr(brain, "candidate_brain", None),
            "candidate_assessment": getattr(brain, "candidate_assessment", None),
            "evidence_requirements": getattr(brain, "evidence_requirements", None),
            "initial_hypotheses": getattr(brain, "initial_hypotheses", None),
            "nodes_executed": getattr(brain, "nodes_executed", []) or [],
        }

    async def _upsert_graph(self, session, session_id: UUID, brain) -> None:
        result = await session.execute(
            select(EvidenceGraphRecord).where(
                EvidenceGraphRecord.session_id == session_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = EvidenceGraphRecord(session_id=session_id)
            session.add(record)

        graph = getattr(brain, "evidence_graph", {}) or {}
        record.nodes = graph.get("nodes", {}) or {}
        record.edges = graph.get("edges", {}) or {}
        record.version = int(getattr(brain, "state_version", 0) or 0) + 1

    async def _append_timeline(self, session, session_id: UUID, brain) -> None:
        session.add(
            InterviewTimelineRecord(
                session_id=session_id,
                event_type="brain_snapshot",
                question_number=getattr(brain, "question_number", 0),
                event_data={
                    "version": int(getattr(brain, "state_version", 0) or 0) + 1,
                    "phase": getattr(brain, "current_phase", None),
                    "difficulty_level": getattr(brain, "difficulty_level", None),
                    "evidence_count": len(getattr(brain, "evidence_store", []) or []),
                    "hypothesis_count": len(getattr(brain, "hypotheses", []) or []),
                },
            )
        )
