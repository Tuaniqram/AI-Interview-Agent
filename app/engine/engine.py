"""InterviewEngine — the V5 orchestration entry point.

Thin coordinator over the split engine modules:

* ``app.engine.lifecycle``     — session start chain
* ``app.engine.answer_processor`` — answer intake (sanitize/evaluate/evidence)
* ``app.engine.routing``       — reflection → difficulty governor → next question
* ``app.engine.decision``      — finalization (synthesis → decision → report)
* ``app.engine.persistence``   — best-effort DB writes
* ``app.engine.builders``      — response payloads

The engine speaks plain dicts at the agent boundary (agents keep their V4
signatures) and reconciles through an ``InterviewBrain`` between turns so the
persistent reasoning state is always authoritative. It is also the seam where
V5 company/candidate intelligence is injected before a session starts.
"""
from typing import Optional

from app.core.interview_brain import InterviewBrain
from app.core.interview_state import dict_to_brain
from app.engine.builders import build_state_response
from app.services.event_log import get_event_log
from app.services.v4_session_store import get_v4_session_store

_V5_FLOW_TYPES = {"v5_evidence_driven", "v5_company_context", "difficulty_probing"}


class InterviewEngine:
    """V5 orchestrator. Injects V4-style dicts into agents, manages brains."""

    def __init__(self, store=None, event_log=None, v5_persister=None):
        self._store = store
        self._events = event_log
        self._v5_persister = v5_persister

    # ------------------------------------------------------------------ #
    # Store / event helpers
    # ------------------------------------------------------------------ #

    def _get_store(self):
        return self._store if self._store is not None else get_v4_session_store()

    def _get_events(self):
        return self._events if self._events is not None else get_event_log()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def start_session(self, state: dict, build_intelligence: bool = False, **intelligence) -> dict:
        """Run the start node chain over a seeded V4-style state dict.

        ``intelligence`` may carry ``company_brain``, ``interview_blueprint``,
        ``candidate_brain``, ``initial_hypotheses``, ``evidence_requirements``
        and ``candidate_assessment`` — all of which are merged into the brain
        and thus visible to every downstream agent.

        When ``build_intelligence`` is True and no intelligence kwargs are
        supplied, the V5 intelligence module produces the bundle from the
        session fields (job role, department, candidate profile/resume,
        scorecard competencies). Every stage is best-effort.

        Returns the ``{type: question}`` response dict.
        """
        from app.engine.lifecycle import start_session as _start

        return await _start(self, state, build_intelligence, intelligence)

    async def process_answer(self, session_id: str, answer: str) -> dict:
        """Sanitize/evaluate/extract evidence, then route the next step."""
        from app.engine.answer_processor import process_answer as _process

        return await _process(self, session_id, answer)

    def get_state(self, session_id: str) -> dict:
        """Return the status snapshot (get_status message)."""
        raw = self._get_store().get(session_id)
        if raw is None:
            raise KeyError(session_id)
        return build_state_response(session_id, raw)

    def get_brain(self, session_id: str) -> InterviewBrain:
        """Hydrate the authoritative ``InterviewBrain`` for a session."""
        raw = self._get_store().get_or_raise(session_id)
        return dict_to_brain(raw)


_engine: Optional[InterviewEngine] = None


def get_engine() -> InterviewEngine:
    """Singleton engine. Store resolved lazily per call for test seam-ability."""
    global _engine
    if _engine is None:
        _engine = InterviewEngine()
    return _engine
