import logging
from uuid import uuid4

from app.graph.interview_state import InterviewState
from app.agents.hypothesis_manager import (
    generate_initial_hypotheses,
    update_hypotheses,
    next_target,
)

logger = logging.getLogger(__name__)


async def hypothesis_node(state: InterviewState) -> InterviewState:
    hypotheses = state.get("hypotheses", [])
    session_id = state.get("session_id", "")
    candidate_profile = state.get("candidate_profile", {})
    job_role = state.get("job_role", "Unknown")
    extracted_evidence = state.get("extracted_evidence", [])
    competency_summary = state.get("competency_summary", {})
    required_competencies = state.get("required_competencies", [])

    if not hypotheses:
        hypotheses = generate_initial_hypotheses(job_role, candidate_profile)

        hypo_state = {}
        for h in hypotheses:
            h["session_id"] = session_id
            h["id"] = h.get("id") or str(uuid4())
            hypo_state[h["id"]] = {"statement": h["statement"], "status": h["status"]}

        target = next_target(hypotheses)

        return {
            **state,
            "hypotheses": hypotheses,
            "hypothesis_state": hypo_state,
            "hypothesis_target": target,
        }

    if extracted_evidence:
        evidence_records = [
            {
                "competency": ev.get("competency", ""),
                "dimension": ev.get("dimension", ""),
                "score": ev.get("score", 0.0),
                "confidence": ev.get("confidence", 0.5),
                "evidence_text": ev.get("evidence_text", ""),
            }
            for ev in extracted_evidence
        ]

        hypotheses = update_hypotheses(hypotheses, evidence_records)

    target = next_target(hypotheses)

    return {
        **state,
        "hypotheses": hypotheses,
        "hypothesis_target": target,
    }
