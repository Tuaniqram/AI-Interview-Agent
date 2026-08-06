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

    from app.engine.builders import build_report_response, refresh_hiring_recommendation
    from app.agents.evaluation.synthesis import synthesis_node

    s = brain_to_dict(brain)
    # Fold the last answer's evidence into the hypotheses before finalizing so
    # the report's outcomes/recommendation reflect every answer (the FINISH
    # path skips the post-evidence hypothesis update in routing).
    from app.agents.reasoning.hypothesis_engine import _requirements_map, update_hypotheses

    if s.get("extracted_evidence"):
        s["hypotheses"] = update_hypotheses(
            s.get("hypotheses", []),
            s["extracted_evidence"],
            required_evidence_map=_requirements_map(s),
        )
    s["hiring_recommendation"] = refresh_hiring_recommendation(s)
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
    await persist_v5_snapshot(session_id, brain, engine._v5_persister, finalize=True)
    await events.append(session_id, "interview_finished", {
        "final_score": brain.evaluation_score,
        "hiring_recommendation": brain.hiring_recommendation,
        "questions_answered": brain.question_number,
    })
    return report
