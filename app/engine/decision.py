"""V5 decision — the finalization chain.

Runs synthesis → hiring decision (and later the decision review pass) over the
completed brain, persists completion, and builds the report payload. The
Decision Review stage is layered in on top of this module as the engine's
"Evidence → Draft → Self Review → Final" capability.
"""
import logging

from app.core.interview_brain import InterviewBrain
from app.core.interview_state import brain_to_dict, sync_brain
from app.engine.persistence import (
    persist_answer_turn,
    persist_completion,
    persist_v5_snapshot,
)

logger = logging.getLogger(__name__)


async def finalize_session(engine, brain: InterviewBrain) -> dict:
    store = engine._get_store()
    events = engine._get_events()
    session_id = brain.session_id

    from app.engine.builders import build_report_response
    from app.agents.evaluation.synthesis import synthesis_node

    s = brain_to_dict(brain)
    try:
        s = await synthesis_node(s)
    except Exception as e:
        logger.warning(f"Synthesis failed (non-fatal): {type(e).__name__}")
    brain = sync_brain(brain, s)

    from app.agents.decision.hiring_decision import hiring_decision_node
    s = await hiring_decision_node(s)
    brain = sync_brain(brain, s)

    from app.agents.decision.decision_review import decision_review_node
    s = await decision_review_node(s)
    brain = sync_brain(brain, s)

    await persist_answer_turn(session_id, brain)
    await persist_completion(session_id, brain)
    store.set(session_id, brain.to_dict())
    store.checkpoint(session_id, brain.to_dict())
    brain.bump_version()

    report = build_report_response(brain)
    report["interview_complete"] = True
    await persist_v5_snapshot(session_id, brain, engine._v5_persister)
    await events.append(session_id, "interview_finished", {
        "final_score": brain.evaluation_score,
        "hiring_recommendation": brain.hiring_recommendation,
        "questions_answered": brain.question_number,
    })
    return report
