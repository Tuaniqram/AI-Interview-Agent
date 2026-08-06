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


async def process_answer(engine, session_id: str, answer: str) -> dict:
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

    from app.engine.routing import route_answer

    return await route_answer(engine, brain, session_id, question_number)
