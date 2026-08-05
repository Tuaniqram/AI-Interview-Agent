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
    from app.agents.reasoning.reflection_engine import reflection_engine

    prev_hypotheses = list(brain.hypotheses)

    s = brain_to_dict(brain)
    s = await reflection_engine(s)
    await events.append(session_id, "action_decided", {
        "question_number": question_number,
        "reflection_action": s.get("reflection_action"),
    })
    brain = sync_brain(brain, s)

    from app.agents.decision.director import director_controller

    director = director_controller(brain_to_dict(brain))
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

    s = brain_to_dict(brain)
    s = await question_generator_node(s)
    brain = sync_brain(brain, s)
    await events.append(session_id, "question_asked", {
        "question_number": brain.question_number,
        "phase": brain.current_phase,
        "difficulty_level": brain.difficulty_level,
    })

    await persist_answer_turn(session_id, brain)
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
