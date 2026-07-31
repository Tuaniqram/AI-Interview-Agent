import logging
from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.graph.interview_state import InterviewState
from app.repositories.evidence_repository import EvidenceRepository
from app.agents.hypothesis_manager import update_hypotheses

logger = logging.getLogger(__name__)

_DIMENSION_KEYS = {"technical", "communication", "reasoning", "behavioral", "confidence", "completeness"}
SAVE_INTERVAL = 2


async def evidence_extractor_node(state: InterviewState) -> InterviewState:
    evaluation = state.get("unified_evaluation", {})
    if not evaluation:
        logger.warning("No evaluation to extract evidence from")
        return state

    question = state.get("current_question", "")
    question_number = state.get("question_number", 0)
    session_id = state.get("session_id", "")
    question_objective = state.get("question_objective", {}) or {}
    target_comp = question_objective.get("target_competency", "")

    extracted = []
    evidence_records = []

    for dim, data in evaluation.items():
        if dim not in _DIMENSION_KEYS:
            continue
        if not isinstance(data, dict):
            continue

        score = data.get("score")
        if score is None:
            continue

        evidence_text = data.get("evidence", "")
        confidence = data.get("confidence", 0.5)
        strengths = data.get("strengths", []) or []
        weaknesses = data.get("weaknesses", []) or []

        competency = target_comp if target_comp else f"dim_{dim}"

        evidence_id = str(uuid4())
        evidence_item = {
            "id": evidence_id,
            "session_id": session_id,
            "competency": competency,
            "dimension": dim,
            "score": float(score),
            "confidence": float(confidence),
            "evidence_text": evidence_text,
            "source_question": question,
            "question_number": question_number,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }
        extracted.append(evidence_item)
        evidence_records.append(evidence_item)

    if not extracted:
        logger.info("No scored dimensions to extract evidence from")
        return state

    competency_summary = _update_competency_summary(
        state.get("competency_summary", {}), extracted
    )

    hypotheses = state.get("hypotheses", [])
    if hypotheses and evidence_records:
        hypotheses = update_hypotheses(hypotheses, evidence_records)

    answer_count = state.get("question_number", 0)
    should_save_db = answer_count % SAVE_INTERVAL == 0 and session_id

    if should_save_db:
        repo = EvidenceRepository()
        for ev in evidence_records:
            try:
                await repo.create_evidence(
                    session_id=session_id,
                    competency=ev["competency"],
                    dimension=ev["dimension"],
                    score=ev["score"],
                    evidence_text=ev["evidence_text"],
                    source_question=ev["source_question"],
                    question_number=ev["question_number"],
                    confidence=ev["confidence"],
                )
            except Exception as e:
                logger.warning(f"Failed to save evidence: {e}")

    existing_evidence = state.get("evidence_store", [])
    existing_evidence.extend(extracted)

    return {
        **state,
        "extracted_evidence": extracted,
        "evidence_store": existing_evidence,
        "competency_summary": competency_summary,
        "hypotheses": hypotheses,
    }


def _update_competency_summary(
    current_summary: dict,
    evidence_list: list[dict],
) -> dict:
    summary = dict(current_summary)

    for ev in evidence_list:
        comp = ev["competency"]
        score = ev["score"]
        confidence = ev["confidence"]

        if comp not in summary:
            summary[comp] = {
                "evidence_count": 0,
                "scores": [],
                "average_score": 0.0,
                "average_confidence": 0.0,
                "latest_score": score,
                "latest_evidence": ev.get("evidence_text", ""),
                "coverage": 0.0,
                "gap": 1.0,
            }

        s = summary[comp]
        s["evidence_count"] += 1
        s["scores"].append(score)
        s["latest_score"] = score
        s["latest_evidence"] = ev.get("evidence_text", "")
        s["average_score"] = round(sum(s["scores"]) / s["evidence_count"], 2)
        s["average_confidence"] = round(
            (s["average_confidence"] * (s["evidence_count"] - 1) + confidence) / s["evidence_count"],
            2,
        )

    return summary
