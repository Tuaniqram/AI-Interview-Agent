"""V5 routing — the per-turn orchestration after evidence is committed.

Owns the reflection/director cycle, the difficulty governor placement and the
question emission + persistence boundary. Pure routing: the heavy capability
modules (reflection, hypothesis selection, question generation) live in
``app/agents/`` and are imported here at call sites so the engine stays thin.
"""
import logging
from typing import Optional

from app.core.interview_brain import InterviewBrain
from app.core.interview_state import brain_to_dict, sync_brain
from app.engine.persistence import persist_answer_turn, summarize_hypotheses

logger = logging.getLogger(__name__)


def _refresh_target_reference(brain: InterviewBrain) -> None:
    """Re-point ``hypothesis_target`` at the live hypothesis object.

    The evaluator replaces hypothesis dicts with updated copies every turn
    (``hypothesis_engine.update_hypotheses``), so ``brain.hypothesis_target``
    can still reference the pre-evaluation dict with stale status/confidence.
    The director decides PROBE vs CONTINUE from that state — refresh it first
    so follow-ups on established beliefs correctly flip to ``deep_probe``.
    """
    target = brain.hypothesis_target or {}
    target_id = target.get("id")
    if not target_id:
        return
    for h in brain.hypotheses or []:
        if h.get("id") == target_id:
            brain.hypothesis_target = h
            return


def _project_target_evidence(state: dict) -> dict:
    """Project pending evidence onto the hypothesis target (pure, non-committing).

    ``hypothesis_node`` is the only place evidence updates hypothesis
    status/confidence, and it runs *after* the director — so at decision time
    the target still shows pre-evidence status and every follow-up looks
    untested, falling through to CONTINUE/explore_new_competency instead of
    PROBE/deep_probe. This applies the pending ``extracted_evidence`` to a copy
    of the target so the director decides on the state the hypothesis is about
    to be in. Nothing is committed: ``hypothesis_node`` still performs the
    single real update, so evidence is never double-counted.
    """
    evidence = state.get("extracted_evidence") or []
    target = state.get("hypothesis_target") or {}
    if not evidence or not target.get("id"):
        return state

    from app.agents.reasoning.hypothesis_engine import update_hypotheses

    records = [
        {
            "id": ev.get("id", ""),
            "competency": ev.get("competency", ""),
            "dimension": ev.get("dimension", ""),
            "score": ev.get("score", 0.0),
            "confidence": ev.get("confidence", 0.5),
            "evidence_text": ev.get("evidence_text", ""),
        }
        for ev in evidence
    ]
    projected = update_hypotheses([dict(target)], records)
    if projected:
        state = {**state, "hypothesis_target": projected[0]}
    return state


async def reflect_and_select(
    engine,
    brain: InterviewBrain,
    session_id: str,
    question_number: int,
    events,
) -> tuple[InterviewBrain, Optional[dict]]:
    """Run reflection, action routing, and hypothesis selection.

    Returns ``(brain, finished_response)`` — when the flow decides to finish,
    the response dict is returned and the caller must short-circuit.
    """
    from app.agents.reasoning.claim_validator import validate_answers
    from app.agents.reasoning.reflection_engine import reflection_engine

    # F5: refresh authenticity signals over every answer so far.
    user_answers = [
        str(h.get("content", "")).strip()
        for h in (brain.conversation_history or [])
        if h.get("role") == "user" and str(h.get("content", "")).strip()
    ]
    if user_answers:
        brain.claim_signals = validate_answers(user_answers)

    prev_hypotheses = list(brain.hypotheses)

    s = brain_to_dict(brain)
    s = await reflection_engine(s)
    await events.append(session_id, "action_decided", {
        "question_number": question_number,
        "reflection_action": s.get("reflection_action"),
    })
    brain = sync_brain(brain, s)

    # AURA V5: re-run the live brain layers so the planner/strategy always see
    # the freshest uncertainty, contradiction and calibration state.
    from app.brain.assembler import refresh_brain_layers

    brain = refresh_brain_layers(brain)

    # Re-point the target at the post-evaluation hypothesis before the director
    # reads it, so fresh status/confidence drive PROBE vs CONTINUE correctly.
    _refresh_target_reference(brain)

    from app.agents.decision.director import director_controller

    director = director_controller(_project_target_evidence(brain_to_dict(brain)))
    brain.director = director
    await events.append(session_id, "director_decided", {
        "question_number": question_number,
        "action": director["action"],
        "reason": director["reason"],
    })

    action = director["action"]
    hypothesis_updated = False

    if action == "CHANGE_COMPETENCY":
        from app.agents.planning.action_router import route_after_planner
        from app.agents.planning.competency_planner import competency_planner_node
        from app.agents.reasoning.hypothesis_engine import hypothesis_node

        s = brain_to_dict(brain)
        s = await competency_planner_node(s)
        brain = sync_brain(brain, s)
        if route_after_planner(brain_to_dict(brain)) == "finish":
            from app.engine.decision import finalize_session

            return brain, await finalize_session(engine, brain)

        s = brain_to_dict(brain)
        s = await hypothesis_node(s)
        brain = sync_brain(brain, s)
        hypothesis_updated = True

    elif action == "FINISH":
        from app.engine.decision import finalize_session

        return brain, await finalize_session(engine, brain)

    if not hypothesis_updated:
        from app.agents.reasoning.hypothesis_engine import hypothesis_node

        s = brain_to_dict(brain)
        s = await hypothesis_node(s)
        brain = sync_brain(brain, s)

    target = brain.hypothesis_target or {}
    _track_target(brain, target.get("id", ""))

    # Refresh the competency plan every turn (cheap, pure): the planner node
    # only re-runs on CHANGE_COMPETENCY, so between turns the plan would show
    # session-start gaps/coverage and disagree with the fresh competency_summary.
    from app.agents.planning.competency_planner import plan_competencies

    brain.competency_plan = plan_competencies(brain_to_dict(brain))

    # Diagnostic per-question log (STEP 12) — compact but comprehensive.
    try:
        planner_top = (brain.competency_plan or [])[0] if brain.competency_plan else None
        competency_summary = brain.competency_summary or {}
        evidence_gap = ""
        if target and target.get("competency"):
            comp = target.get("competency")
            evidence_gap = competency_summary.get(comp, {}).get("gap", "")
        # The brain carries ``planned_competency``/``next_competency`` as
        # Optional[dict]; older brain shapes only stored the id. Resolve both
        # forms defensively so the diagnostic log never crashes a turn.
        planned = getattr(brain, "planned_competency", None) or ""
        planned_id = planned.get("id") if isinstance(planned, dict) else planned
        next_c = getattr(brain, "next_competency", None) or ""
        next_id = next_c.get("id") if isinstance(next_c, dict) else next_c
        diag = (
            f"QUESTION {question_number}\n"
            f"Current hypothesis: id={target.get('id','')} status={target.get('status','')} confidence={target.get('confidence','')}\n"
            f"Current competency: planned={planned_id} next={next_id} target={target.get('competency','')}\n"
            f"Reason selected: {target.get('selection_reason','')} info_gain={target.get('information_gain',0.0)}\n"
            f"Evidence gap: {evidence_gap} Coverage:{competency_summary.get(target.get('competency',''),{}).get('coverage','')}\n"
            f"Difficulty: {getattr(brain,'difficulty_level',None)}\n"
            f"Termination: reflection_action={getattr(brain,'reflection_action',None)} "
            f"director_action={(getattr(brain,'director',None) or {}).get('action',None)} "
            f"planner_top={planner_top.get('id') if isinstance(planner_top, dict) else planner_top}\n"
            f"Questions asked (last5): {[q.get('text') or q.get('content') for q in (brain.questions_asked or [])[-5:]]}\n"
        )
        logger.info(diag)
    except Exception as _:
        logger.exception("Failed to emit diagnostic question log")

    await events.append(session_id, "question_selected", {
        "question_number": question_number,
        "target_hypothesis_id": target.get("id", ""),
        "competency": target.get("competency", ""),
        "status": target.get("status", ""),
        "selection_reason": target.get("selection_reason", ""),
        "information_gain": target.get("information_gain", 0.0),
    })

    before = summarize_hypotheses(prev_hypotheses)
    after = summarize_hypotheses(brain.hypotheses)
    if before != after:
        await events.append(session_id, "hypothesis_updated", {
            "question_number": question_number,
            "before": before,
            "after": after,
        })

    return brain, None


def _track_target(brain: InterviewBrain, target_id: str) -> None:
    """Update the consecutive-probe loop counters for the newly selected target."""
    if target_id and target_id == brain.last_hypothesis_target_id:
        brain.consecutive_probes += 1
    else:
        brain.consecutive_probes = 0
    brain.last_hypothesis_target_id = target_id


async def govern_difficulty(state: dict, question_number: int) -> dict:
    """Conditional-LLM difficulty governor placed after hypothesis selection.

    Uses the governor's own conditional-skip heuristic: the LLM path runs for
    the first four turns, then only when the last read is not decisive. The
    deterministic fallback inside the agent is cheap and avoids one LLM call
    per established turn.
    """
    from app.agents.planning.difficulty_engine import (
        difficulty_governor,
        should_skip_llm_governor,
    )

    state = dict(state)
    state["_prev_difficulty"] = state.get("difficulty_level")
    skip = should_skip_llm_governor(state)
    if question_number < 4:
        return await difficulty_governor(state, use_llm=True)
    try:
        return await difficulty_governor(state, use_llm=not skip)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Difficulty governor failed (non-fatal): {e}")
        return state


async def emit_question_and_persist(
    engine,
    brain: InterviewBrain,
    session_id: str,
    question_number: int,
    events,
) -> dict:
    """Run question generation, persist the turn, store the brain, respond."""
    store = engine._get_store()
    from app.engine.builders import build_answer_response
    from app.agents.generation.question_generator import question_generator_node

    # Persist the just-answered turn BEFORE generating the next question —
    # ``question_generator_node`` bumps ``question_number`` and
    # ``extract_answer_turn`` stamps the turn with the brain's number, so
    # persisting after generation mislabeled every row one question late
    # (Q1's turn persisted as Q2, final answer never flushed).
    await persist_answer_turn(session_id, brain)

    s = brain_to_dict(brain)
    s = await question_generator_node(s)
    brain = sync_brain(brain, s)
    from app.services.anti_cheat import now_iso

    brain.question_asked_at = now_iso()

    # Diagnostic log for emitted question (post-generation)
    try:
        qobj = getattr(brain, 'question_objective', {}) or {}
        comp_summary = brain.competency_summary or {}
        logger.info(
            {
                'question_number': brain.question_number,
                'current_question': getattr(brain, 'current_question', ''),
                'question_objective': qobj,
                'target_hypothesis_id': qobj.get('target_hypothesis_id'),
                'target_competency': qobj.get('target_competency'),
                'difficulty_level': getattr(brain, 'difficulty_level', None),
                'competency_coverage': comp_summary.get(qobj.get('target_competency',''), {}).get('coverage'),
                'planner_top': (brain.competency_plan or [None])[0] if brain.competency_plan else None,
            }
        )
    except Exception:
        logger.exception('Failed to log emitted question diagnostic')

    await events.append(session_id, "question_asked", {
        "question_number": brain.question_number,
        "phase": brain.current_phase,
        "difficulty_level": brain.difficulty_level,
    })

    store.set(session_id, brain.to_dict())
    store.checkpoint(session_id, brain.to_dict())
    brain.bump_version()

    logger.info(
        f"v5 answer processed: session={session_id[:12]}..., q#{question_number}"
    )
    return build_answer_response(session_id, brain)


async def route_answer(
    engine,
    brain: InterviewBrain,
    session_id: str,
    question_number: int,
) -> dict:
    """Unified post-evidence pipeline: reflect/select → governor → emit.

    All flow types share this path; the conditional difficulty governor runs
    after hypothesis selection so it adapts to the target about to be asked.
    """
    events = engine._get_events()

    brain, finished = await reflect_and_select(
        engine, brain, session_id, question_number, events
    )
    if finished is not None:
        return finished

    s = brain_to_dict(brain)
    s = await govern_difficulty(s, question_number)
    await events.append(session_id, "difficulty_changed", {
        "question_number": question_number,
        "prev_difficulty": s.get("_prev_difficulty"),
        "difficulty_level": s.get("difficulty_level"),
    })
    brain = sync_brain(brain, s)

    response = await emit_question_and_persist(
        engine, brain, session_id, question_number, events
    )
    from app.engine.persistence import persist_v5_snapshot

    await persist_v5_snapshot(session_id, brain, engine._v5_persister)
    return response
