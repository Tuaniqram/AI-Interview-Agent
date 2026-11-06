"""V5 brain persistence — the durable snapshot of the interview reasoning state.

Writes the three V5 tables (``interview_brain``, ``evidence_graph``,
``interview_timeline``) after every V5 turn and on finalize. It is the concrete
implementation of the engine's opt-in ``v5_persister`` seam: pass an instance to
``InterviewEngine(v5_persister=...)`` and the engine calls ``save_snapshot(brain)``
at the turn boundary. Failures are non-fatal by design (persistence must never
break an interview), and the session factory can be injected for tests.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.session import get_session_factory
from app.models.db import (
    Hypothesis as HypothesisRecord,
    InterviewBrain as InterviewBrainRecord,
    InterviewIntelligence,
    InterviewTimeline as InterviewTimelineRecord,
    ScorecardResult as ScorecardResultRecord,
)

logger = logging.getLogger(__name__)


def _uuid_list(items) -> list | None:
    """Coerce a list of uuid-strings/uuid objects into UUIDs (invalid dropped)."""
    out = []
    for it in items or []:
        try:
            out.append(UUID(str(it)))
        except (ValueError, TypeError, AttributeError):
            continue
    return out


def _clamp(value, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return lo


def _coerce_dt(value) -> datetime:
    """Coerce a brain-carried timestamp into a tz-aware datetime.

    The InterviewBrain JSON-round-trips through the session store, so
    timestamps arrive as ISO strings (or naive datetimes); asyncpg rejects
    both for timestamptz columns and would abort the whole finalize
    transaction.
    """
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
    else:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _backfill_evidence_summary(summary: dict, required_competencies: list) -> dict:
    """Union zero-evidence required competencies into the evidence summary.

    ``competency_summary`` only contains competencies that have collected
    evidence, so the brain view's ``evidence_summary`` silently dropped
    unprobed required competencies while ``evidence_sufficiency.details``
    listed them with ``gap=1.0``. Backfilling at the serialization boundary
    makes both surfaces agree without touching the live scoring state.
    """
    out = dict(summary or {})
    for comp in required_competencies or []:
        if comp in out:
            continue
        out[comp] = {
            "evidence_count": 0,
            "average_score": 0.0,
            "average_confidence": 0.0,
            "average_strength": 0.0,
            "coverage": 0.0,
            "gap": 1.0,
        }
    return out


class V5BrainPersister:
    """Upsert the V5 reasoning snapshot for a session."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or get_session_factory
        self._last_objective_key: dict[str, str] = {}
        self._last_objective_row_id: dict[str, UUID] = {}
        self._last_obs_qnum: dict[str, int] = {}
        self._finalize_done: dict[str, bool] = {}

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
            await self._upsert_intelligence(session, session_id, brain)
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
        record.evidence_summary = _backfill_evidence_summary(
            getattr(brain, "competency_summary", {}) or {},
            getattr(brain, "required_competencies", None) or [],
        )
        nodes = (getattr(brain, "evidence_graph", {}) or {}).get("nodes", {}) or {}
        record.competency_scores = nodes
        record.difficulty_profile = getattr(brain, "difficulty_profile", None)
        record.decision_state = {
            "reflection_action": getattr(brain, "reflection_action", None),
            "director": getattr(brain, "director", {}) or {},
            "consecutive_probes": int(getattr(brain, "consecutive_probes", 0) or 0),
            # The deterministic final decision (single source of truth per the
            # engine contract) is persisted so the brain view surfaces the
            # verdict alongside the recommendation.
            "hiring_decision": getattr(brain, "hiring_decision", {}) or {},
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
            # AURA V5 layers: the full assembled brain plus the per-turn
            # signals the planner/calibration expose after every answer.
            "aura_brain": getattr(brain, "aura_brain", None),
            "uncertainty_map": getattr(brain, "uncertainty_map", {}) or {},
            "question_strategy": getattr(brain, "question_strategy", None),
            "contradiction_state": getattr(brain, "contradiction_state", {}) or {},
            "calibration_state": getattr(brain, "calibration_state", {}) or {},
            "candidate_memory": getattr(brain, "candidate_memory", {}) or {},
        }

    async def _upsert_intelligence(self, session, session_id: UUID, brain) -> None:
        result = await session.execute(
            select(InterviewIntelligence).where(
                InterviewIntelligence.session_id == session_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = InterviewIntelligence(session_id=session_id)
            session.add(record)

        record.company_context = getattr(brain, "company_brain", {}) or {}
        record.candidate_context = getattr(brain, "candidate_brain", {}) or {}
        record.blueprint = getattr(brain, "interview_blueprint", {}) or {}
        record.scorecard = {
            "competencies": getattr(brain, "competency_taxonomy", []) or [],
            "scores": getattr(brain, "competency_summary", {}) or {},
        }
        record.evidence_requirements = getattr(brain, "evidence_requirements", []) or []
        objective = getattr(brain, "question_objective", None)
        record.objectives = [objective] if objective else []
        record.consistency_checks = getattr(brain, "consistency_checks", []) or []
        record.observations = getattr(brain, "observations", []) or []
        record.evidence_graph = getattr(brain, "evidence_graph", {}) or {}

    async def _append_timeline(self, session, session_id: UUID, brain) -> None:
        qnum = int(getattr(brain, "question_number", 0) or 0)
        event_data = {
            "version": int(getattr(brain, "state_version", 0) or 0) + 1,
            "phase": getattr(brain, "current_phase", None),
            "difficulty_level": getattr(brain, "difficulty_level", None),
            "evidence_count": len(getattr(brain, "evidence_store", []) or []),
            "hypothesis_count": len(getattr(brain, "hypotheses", []) or []),
        }
        # B1: the engine persists a snapshot after every turn *and* again at
        # finalize, so the last question would otherwise emit two identical
        # brain_snapshot rows (15 events / 14 questions). Upsert per
        # (session, question_number) keeps one snapshot per question.
        existing = await session.execute(
            select(InterviewTimelineRecord).where(
                InterviewTimelineRecord.session_id == session_id,
                InterviewTimelineRecord.event_type == "brain_snapshot",
                InterviewTimelineRecord.question_number == qnum,
            )
        )
        record = existing.scalars().first()
        if record is not None:
            record.event_data = event_data
            session.add(record)
            return
        session.add(
            InterviewTimelineRecord(
                session_id=session_id,
                event_type="brain_snapshot",
                question_number=qnum,
                event_data=event_data,
            )
        )

    # ------------------------------------------------------------------ #
    # Relational V4 tables (hypotheses / observations / objectives /
    # consistency_checks) — best-effort, never raises.
    # ------------------------------------------------------------------ #

    async def save_relational(self, brain, finalize: bool = False) -> None:
        """Best-effort writes to the relational reasoning tables.

        ``finalize`` marks the last objective as probed and persists
        consistency checks (which are only complete at the end).
        """
        session_id_str = getattr(brain, "session_id", "")
        if not session_id_str:
            return
        try:
            session_id = UUID(session_id_str)
        except (ValueError, TypeError, AttributeError):
            logger.warning(
                f"Invalid session_id for v5 relational snapshot: {session_id_str!r}"
            )
            return

        if finalize and self._finalize_done.get(str(session_id)):
            return
        self._finalize_done[str(session_id)] = True

        factory = self._session_factory()
        if factory is None:
            logger.debug("v5 relational persister no-op: DATABASE_URL not configured")
            return

        try:
            async with factory() as session:
                await self._upsert_hypotheses(session, session_id, brain)
                await self._upsert_intelligence(session, session_id, brain)
                if finalize:
                    await self._insert_scorecard_result(session, session_id, brain)
                await session.commit()
        except Exception as exc:  # noqa: BLE001 - best-effort by design
            logger.error(f"V5 relational persistence failed (finalize={finalize})", exc_info=exc)

    async def _upsert_hypotheses(self, session, session_id: UUID, brain) -> None:
        hypotheses = getattr(brain, "hypotheses", []) or []
        if not hypotheses:
            return
        rows = []
        for h in hypotheses:
            try:
                hid = UUID(str(h.get("id", "")))
            except (ValueError, TypeError):
                continue
            rows.append({
                "id": hid,
                "session_id": session_id,
                "statement": h.get("statement") or "",
                "competency_id": h.get("competency"),
                "direction": h.get("direction") or "positive",
                "confidence": _clamp(h.get("confidence", h.get("probability", 0.0))),
                "supporting_evidence": _uuid_list(h.get("supporting_evidence")),
                "contradicting_evidence": _uuid_list(h.get("contradicting_evidence")),
                "status": h.get("status") or "untested",
            })
        if not rows:
            return
        stmt = pg_insert(HypothesisRecord).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[HypothesisRecord.id],
            set_={
                "statement": stmt.excluded.statement,
                "competency_id": stmt.excluded.competency_id,
                "direction": stmt.excluded.direction,
                "confidence": stmt.excluded.confidence,
                "supporting_evidence": stmt.excluded.supporting_evidence,
                "contradicting_evidence": stmt.excluded.contradicting_evidence,
                "status": stmt.excluded.status,
                "last_updated": func.now(),
            },
        )
        await session.execute(stmt)

    async def _insert_observations(self, session, session_id: UUID, brain) -> None:
        observations = getattr(brain, "observations", []) or []
        if not observations:
            return
        key = str(session_id)
        answered = getattr(brain, "answered_question_numbers", []) or []
        qnum = answered[-1] if answered else int(getattr(brain, "question_number", 0) or 0)
        if qnum == self._last_obs_qnum.get(key):
            return
        existing_obs = await session.execute(
            select(ObservationRecord.id)
            .where(
                ObservationRecord.session_id == session_id,
                ObservationRecord.question_number == qnum,
            )
            .limit(1)
        )
        if existing_obs.scalar_one_or_none() is not None:
            return
        self._last_obs_qnum[key] = qnum
        risk_types = {"hedging", "certainty_shift", "sentiment_shift", "response_latency_estimate"}
        for obs in observations:
            obs_type = obs.get("type") or "observation"
            raw_value = obs.get("value")
            evidence = obs.get("evidence") or (
                f"{obs_type}={float(raw_value):.2f}"
                if isinstance(raw_value, (int, float))
                else (str(raw_value) if raw_value else "")
            )
            risk_signal = obs.get("risk_signal")
            if risk_signal is None:
                risk_signal = {"signal": obs_type} if obs_type in risk_types else None
            session.add(ObservationRecord(
                session_id=session_id,
                question_number=qnum,
                type=obs_type,
                value=_clamp(raw_value, 0.0, 1.0),
                evidence=evidence,
                pattern=obs.get("pattern") or obs_type,
                risk_signal=risk_signal,
            ))

    async def _upsert_objectives(
        self, session, session_id: UUID, brain, finalize: bool
    ) -> None:
        key = str(session_id)
        objective = getattr(brain, "question_objective", None) or {}
        question_id = objective.get("question_id")
        if not question_id:
            return

        target_competency = objective.get("target_competency") or "unknown"
        evidence_ids = _uuid_list([
            ev.get("id")
            for ev in (getattr(brain, "evidence_store", None) or [])
            if ev.get("competency") == target_competency
        ])

        if self._last_objective_key.get(key) != question_id:
            if self._last_objective_row_id.get(key) is not None:
                await session.execute(
                    update(InterviewObjectiveRecord)
                    .where(InterviewObjectiveRecord.id == self._last_objective_row_id[key])
                    .values(status="probed", evidence_ids=evidence_ids)
                )
            hypotheses = getattr(brain, "hypotheses", []) or []
            target_id = objective.get("target_hypothesis_id") or ""
            match = next((h for h in hypotheses if str(h.get("id", "")) == str(target_id)), None)
            try:
                hypothesis_id = UUID(str(target_id)) if target_id else None
            except (ValueError, TypeError):
                hypothesis_id = None
            new_id = uuid.uuid4()
            row = InterviewObjectiveRecord(
                id=new_id,
                session_id=session_id,
                competency=target_competency,
                dimension=objective.get("dimension")
                or getattr(brain, "current_phase", None)
                or "technical",
                hypothesis_id=hypothesis_id,
                hypothesis_statement=match.get("statement") if match else None,
                hypothesis_confidence=_clamp(match.get("confidence", 0.0)) if match else None,
                status="pending",
                evidence_ids=evidence_ids,
                priority=1,
            )
            session.add(row)
            self._last_objective_row_id[key] = new_id
            self._last_objective_key[key] = question_id
        elif finalize and self._last_objective_row_id.get(key) is not None:
            await session.execute(
                update(InterviewObjectiveRecord)
                .where(InterviewObjectiveRecord.id == self._last_objective_row_id[key])
                .values(status="probed", evidence_ids=evidence_ids)
            )

    async def _insert_consistency_checks(self, session, session_id: UUID, brain) -> None:
        checks = getattr(brain, "consistency_checks", []) or []
        if not checks:
            return
        existing = await session.execute(
            select(ConsistencyCheckRecord.id)
            .where(ConsistencyCheckRecord.session_id == session_id)
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return
        contradictions = getattr(brain, "contradictions", []) or []
        for check in checks:
            score = check.get("score")
            confidence = check.get("confidence", 0.5)
            session.add(ConsistencyCheckRecord(
                session_id=session_id,
                check_type=check.get("type") or "evaluation",
                assessment=check.get("assessment"),
                score=check.get("score"),
                confidence=check.get("confidence"),
                evidence=check.get("evidence", ""),
                checked_at=_coerce_dt(check.get("checked_at")),
                dimension=check.get("type") or "evaluation",
                answers_compared={
                    "assessment": check.get("assessment"),
                    "evidence": check.get("evidence", ""),
                },
                consistency_score=_clamp((score or 0) / 10.0 * _clamp(confidence)),
                contradictions=contradictions,
            ))

    async def _insert_scorecard_result(self, session, session_id: UUID, brain) -> None:
        existing = await session.execute(
            select(ScorecardResultRecord.id)
            .where(ScorecardResultRecord.session_id == session_id)
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return
        scores = {}
        for comp, summary in (getattr(brain, "competency_summary", {}) or {}).items():
            if isinstance(summary, dict):
                scores[comp] = {
                    "score": summary.get("score"),
                    "evidence_count": summary.get("evidence_count", 0),
                    "confidence": summary.get("confidence"),
                }
            else:
                scores[comp] = {"score": summary}
        evaluation_score = getattr(brain, "evaluation_score", None)
        session.add(ScorecardResultRecord(
            session_id=session_id,
            scores=scores or {},
            weighted_score=float(evaluation_score) if evaluation_score is not None else None,
        ))
