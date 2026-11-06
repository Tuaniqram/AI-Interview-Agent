"""V5 answer processor — the per-answer intake pipeline.

Sanitizes the candidate's answer, appends the Q/A turn to the conversation,
evaluates it, extracts evidence and commits it to the store-backed brain. The
post-evidence routing (reflection → governor → next question) lives in
``app.engine.routing``.
"""
import logging

from app.core.interview_brain import InterviewBrain
from app.core.interview_state import brain_to_dict, dict_to_brain, sync_brain
from app.engine.persistence import persist_evidence

logger = logging.getLogger(__name__)


async def process_answer(
    engine, session_id: str, answer: str, integrity_meta: dict | None = None
) -> dict:
    """Sanitize/evaluate/extract evidence, then route the next step."""
    store = engine._get_store()
    events = engine._get_events()

    raw = store.get_or_raise(session_id)
    brain = dict_to_brain(raw)

    from app.utils.input_sanitizer import (
        detect_prompt_injection,
        sanitize_user_input,
    )

    sanitized = sanitize_user_input(answer)
    injections = detect_prompt_injection(answer)
    if injections:
        logger.warning(
            f"Potential prompt injection detected in session {session_id[:12]}: {injections[:3]}"
        )
    answer = sanitized

    # Anti-cheat integrity guard (contract: docs/anti-cheat-guard.md). No-op
    # unless ANTI_CHEAT_GUARD_ENABLED=true. Never raises; stores per-answer
    # signals on the brain for the final report.
    from app.services.anti_cheat import assess, should_terminate

    prior_answers = [
        str(e.get("content", "")).strip()
        for e in (brain.conversation_history or [])
        if e.get("role") == "user" and str(e.get("content", "")).strip()
    ]
    integrity = await assess(
        text=answer,
        question=getattr(brain, "current_question", "") or "",
        question_asked_at=getattr(brain, "question_asked_at", None),
        paste_chars=(integrity_meta or {}).get("paste_chars"),
        focus_lost_count=(integrity_meta or {}).get("focus_lost_count"),
        prior_answers=prior_answers,
        answer_source=(integrity_meta or {}).get("answer_source", ""),
        keystroke_intervals=(integrity_meta or {}).get("keystroke_intervals"),
        first_key_ms=(integrity_meta or {}).get("first_key_ms"),
        pointer_leaves=(integrity_meta or {}).get("pointer_leaves"),
        heartbeat_gaps=(integrity_meta or {}).get("heartbeat_gaps"),
    )
    if integrity is not None:
        integrity = {"question_number": brain.question_number, **integrity}
        brain.integrity_signals = list(getattr(brain, "integrity_signals", None) or []) + [integrity]
        brain.integrity_score = max(
            getattr(brain, "integrity_score", 0) or 0, integrity["score"]
        )
        # Termination policy: reaching ANTI_CHEAT_MAX_FLAGS flagged answers ends
        # the session. The current answer is still evaluated first; the flag is
        # honored after evaluation by short-circuiting the routing below.
        if should_terminate(brain.integrity_signals):
            brain.integrity_terminated = True

    await events.append(session_id, "answer_received", {
        "length": len(answer),
        "injection_signals": list(injections),
    })

    question_number = brain.question_number
    if question_number >= brain.max_questions:
        from app.engine.decision import finalize_session

        return await finalize_session(engine, brain)

    if brain.current_question:
        brain.conversation_history.append(
            {"role": "assistant", "content": brain.current_question}
        )
    brain.conversation_history.append({"role": "user", "content": answer})
    brain.candidate_answer = answer
    brain.skip_evaluation = False
    brain.extracted_evidence = []

    from app.agents.evaluation.candidate_evaluator import unified_evaluator_node
    from app.agents.evaluation.scoring import explainable_scoring_node
    from app.agents.reasoning.evidence_engine import evidence_extractor_node

    s = brain_to_dict(brain)
    s = await unified_evaluator_node(s)
    s = await evidence_extractor_node(s)
    s = explainable_scoring_node(s)
    await persist_evidence(session_id, s)

    # Diagnostic log after evaluation & evidence extraction
    try:
        from app.engine.persistence import summarize_hypotheses as _summ
        extracted = s.get('extracted_evidence', []) or []
        comp_summary = s.get('competency_summary', {}) or {}
        logger.info({
            'question_number': question_number,
            'extracted_evidence_count': len(extracted),
            'extracted_evidence': [ { 'competency': ev.get('competency'), 'dimension': ev.get('dimension'), 'score': ev.get('score') } for ev in extracted ],
            'evidence_store_count': len(s.get('evidence_store', []) or []),
            'competency_summary_snapshot': comp_summary,
            'hypotheses_before_after': _summ(s.get('hypotheses', [])),
        })
    except Exception:
        logger.exception('Failed to emit evaluation diagnostic')

    await events.append(session_id, "evaluation_done", {
        "question_number": question_number,
        "unified_evaluation": s.get("unified_evaluation", {}),
        "evaluation_score": s.get("evaluation_score"),
        "score_reasons": s.get("score_reasons", []),
    })
    await events.append(session_id, "evidence_added", {
        "question_number": question_number,
        "evidence_count": len(s.get("evidence_store", [])),
        "competency_summary": s.get("competency_summary", {}),
    })
    brain = sync_brain(brain, s)

    # Integrity termination (guard enabled + flagged count >= max): the answer
    # was evaluated fairly — no further question is emitted; the session
    # finalizes with the integrity flag surfaced in the report.
    if getattr(brain, "integrity_terminated", False):
        from app.engine.decision import finalize_session

        await events.append(session_id, "integrity_terminated", {
            "question_number": question_number,
            "flagged_count": len(
                [x for x in (getattr(brain, "integrity_signals", None) or []) if x.get("flagged")]
            ),
        })
        return await finalize_session(engine, brain)

    from app.engine.routing import route_answer

    return await route_answer(engine, brain, session_id, question_number)
