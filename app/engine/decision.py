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


def _enrich_recommendation(state: dict, recommendation: dict, sufficiency: dict) -> dict:
    """Add the T2/T4 observability fields the final brain view needs.

    ``dimension_scores`` is the per-competency breakdown for **every**
    competency that is either required for the role OR collected evidence
    during the interview (the union), so it always covers exactly the same set
    as the persisted ``evidence_summary``. ``family`` maps each of those
    competencies to its taxonomy family. Both are pure additions — they never
    alter the verdict, confidence or composite.
    """
    from app.agents.reasoning.contradiction_engine import (
        MIN_QUESTIONS_PER_COMPETENCY,
        SUFFICIENCY_GAP_THRESHOLD,
    )

    rec = dict(recommendation or {})
    details = (sufficiency or {}).get("details") or {}
    summary = state.get("competency_summary") or {}

    dims: dict = {}
    for comp in sorted(set(details) | set(summary)):
        d = details.get(comp)
        if d is not None:
            dims[comp] = {
                "average_score": d.get("average_score", 0.0),
                "evidence_count": d.get("evidence_count", 0),
                "gap": d.get("gap", 1.0),
                "covered": bool(d.get("covered", False)),
            }
            continue
        s = summary.get(comp, {})
        evidence_count = int(s.get("evidence_count", 0) or 0)
        gap = s.get("gap", 1.0)
        dims[comp] = {
            "average_score": s.get("average_score", 0.0),
            "evidence_count": evidence_count,
            "gap": gap,
            "covered": bool(
                evidence_count >= MIN_QUESTIONS_PER_COMPETENCY
                and gap <= SUFFICIENCY_GAP_THRESHOLD
            ),
        }
    rec["dimension_scores"] = dims
    family_by_id = {
        c.get("id"): c.get("family")
        for c in (state.get("competency_taxonomy") or [])
        if isinstance(c, dict) and c.get("id") and c.get("family")
    }
    rec["family"] = {comp: family_by_id.get(comp) for comp in dims}
    return rec


def apply_calibration_verdict(state: dict) -> dict:
    """Drive the report verdict from the V5 calibration brain.

    The calibration layer never lets a shallow interview (thin evidence, low
    difficulty reached) be a hire even when the raw composite is high. It
    overrides the decision chain's draft with the calibrated verdict/score,
    keeping the draft under ``hiring_decision.draft`` for the report. The
    calibrated result is also mirrored into ``hiring_recommendation`` so the
    brain view exposes it next to the uncalibrated recommendation.
    """
    aura = state.get("aura_brain") or {}
    calibration_state = aura.get("calibration_state") or {}
    calibrated_verdict = calibration_state.get("calibrated_verdict")
    if not calibrated_verdict:
        return state
    decision = dict(state.get("hiring_decision") or {})
    decision["draft"] = decision.get("decision")
    decision["decision"] = calibrated_verdict
    calibrated_score = calibration_state.get("calibrated_score")
    if calibrated_score is not None:
        decision["decision_score"] = calibrated_score
    decision["calibration_source"] = "aura_v5_calibration"
    recommendation = dict(state.get("hiring_recommendation") or {})
    recommendation["calibrated_verdict"] = calibrated_verdict
    if calibrated_score is not None:
        recommendation["calibrated_score"] = calibrated_score
    recommendation["calibration_source"] = "aura_v5_calibration"
    return {
        **state,
        "hiring_decision": decision,
        "hiring_recommendation": recommendation,
    }


async def finalize_session(engine, brain: InterviewBrain) -> dict:
    store = engine._get_store()
    events = engine._get_events()
    session_id = brain.session_id

    from app.engine.builders import (
        build_report_response,
        refresh_sufficiency_and_recommendation,
    )
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
    # Refresh BOTH the sufficiency and the recommendation from the same
    # post-update snapshot so the persisted pair never disagrees (e.g. the
    # old code refreshed only the recommendation, leaving evidence_sufficiency
    # with the pre-update ``unanswered_hypotheses``).
    sufficiency, recommendation = refresh_sufficiency_and_recommendation(s)
    s["evidence_sufficiency"] = sufficiency
    s["hiring_recommendation"] = _enrich_recommendation(s, recommendation, sufficiency)
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

    # AURA V5: assemble the full multi-layer brain over the final state so the
    # report carries calibration + contradiction + decision intelligence.
    try:
        from app.brain.assembler import build_aura_from_state

        aura = build_aura_from_state(s)
        brain.aura_brain = aura
        s["aura_brain"] = aura
    except Exception as exc:  # noqa: BLE001 - brain assembly is best-effort
        logger.warning(f"Final AURA brain assembly failed (non-fatal): {exc}")

    # V5 calibration is the source of truth for the verdict: never let a
    # shallow interview be a hire regardless of the raw composite.
    try:
        s = apply_calibration_verdict(s)
        brain.hiring_decision = s.get("hiring_decision")
        brain.hiring_recommendation = s.get("hiring_recommendation")
    except Exception as exc:  # noqa: BLE001 - calibration override is best-effort
        logger.warning(f"Calibration verdict override failed (non-fatal): {exc}")

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
