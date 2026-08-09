"""V5 evidence-reading node — semantic read of the raw answers at finalization.

Runs the LLM over the actual candidate answers (``evidence_text``) and maps the
response into a deterministic ``evidence_reading`` dict on the state. The
reading is a *signal* for the deterministic layers — it refines claim
classifications (downgrade-only), adds off-rubric red flags and cross-answer
risks, and feeds the decision review. It never scores and never sets a verdict.

Any failure degrades to the current deterministic behavior: the state is
returned unchanged.
"""
import json
import logging

from app.agents.reasoning.evidence_reading import (
    map_evidence_reading,
    transcript_payload,
)

logger = logging.getLogger(__name__)


async def evidence_reading_node(state: dict) -> dict:
    """Read the raw answers semantically and attach ``state["evidence_reading"]``."""
    evidence = state.get("evidence_store") or []
    if not evidence:
        return state

    reading = None
    try:
        from app.services.llm_service import get_llm_service
        from app.services.prompt_loader import load_prompt

        payload = transcript_payload(evidence)
        llm_service = get_llm_service()
        prompt = load_prompt(
            "evaluation",
            "evidence_reading.md",
            job_role=state.get("job_role", "Unknown"),
            evidence_transcript=json.dumps(payload, ensure_ascii=False, indent=2),
        )
        response = await llm_service.invoke(
            prompt=prompt, temperature=0.1, max_tokens=1500, tier="strong"
        )

        from app.intelligence._helpers import parse_json

        try:
            data = parse_json(response)
        except ValueError:
            data = None

        if data:
            reading = map_evidence_reading(evidence, data)
    except Exception as exc:  # noqa: BLE001 - evidence reading is best-effort
        logger.warning(f"Evidence reading LLM failed ({exc}); keeping deterministic path")

    if not reading:
        return state

    logger.info(f"Evidence reading complete: {len(reading.get('per_answer', {}))} answer(s) read")
    return {**state, "evidence_reading": reading}
