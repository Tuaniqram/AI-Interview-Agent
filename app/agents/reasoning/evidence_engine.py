"""V5 evidence engine — extracting and structuring candidate evidence.

Pure capability that turns an evaluation dict into evidence records and folds
them into the competency summary + evidence graph. It never touches the
database (the engine owns persistence) and never mutates shared state.

Evidence quality signals computed per record:
    confidence   — the LLM's stated confidence in the dimension score
    strength     — score magnitude tempered by confidence (0..1)
    impact       — how decisive the evidence is (confidence × |score−5|/5)
    ownership    — first-person attribution signal
    complexity   — specificity/depth signal from the raw answer
    contradiction— conflicts with the competency's prior average score
"""
import logging
import re
from uuid import uuid4

from app.agents.reasoning.hypothesis_engine import compute_relevance

logger = logging.getLogger(__name__)

_DIMENSION_KEYS = {
    "technical",
    "communication",
    "reasoning",
    "behavioral",
    "confidence",
    "completeness",
}

# How often (in answered questions) evidence rows are flushed to the DB. The
# engine reads this; the capability itself stays write-free.
SAVE_INTERVAL = 2

# A score this far from a competency's running average flags an inconsistency.
CONTRADICTION_DELTA = 4.0

_FIRST_PERSON_VERBS = {
    "built", "led", "designed", "implemented", "created", "owned", "drove",
    "fixed", "shipped", "architected", "developed", "engineered", "wrote",
    "scaled", "migrated", "reduced", "launched", "managed", "delivered",
}
_TECH_TERMS = {
    "database", "sql", "nosql", "api", "queue", "cache", "system", "design",
    "scale", "scaling", "latency", "throughput", "kubernetes", "docker",
    "microservice", "microservices", "pipeline", "distributed", "cluster",
    "index", "replica", "load", "circuit", "retry", "timeout", "algorithm",
}

__all__ = [
    "_DIMENSION_KEYS",
    "SAVE_INTERVAL",
    "CONTRADICTION_DELTA",
    "build_evidence_records",
    "update_competency_summary",
    "update_evidence_graph",
    "annotate_evidence_quality",
    "compute_evidence_strength",
    "compute_evidence_impact",
    "ownership_signal",
    "complexity_signal",
    "detect_evidence_contradiction",
    "_supports_hypothesis",
    "evidence_extractor_node",
]


def compute_evidence_strength(score: float, confidence: float) -> float:
    """Evidence strength (0..1): score magnitude tempered by confidence."""
    return round(max(0.0, min(1.0, (float(score) / 10.0) * float(confidence))), 4)


def compute_evidence_impact(score: float, confidence: float) -> float:
    """Evidence impact (0..1): how decisive the evidence is.

    Maxes out when the score is strongly off-midpoint (5.0) and confidence is
    high — extreme, confident evidence moves beliefs the most.
    """
    deviation = abs(float(score) - 5.0) / 5.0
    return round(max(0.0, min(1.0, deviation * float(confidence))), 4)


def ownership_signal(evidence_text: str) -> str:
    """First-person attribution signal of an answer.

    Returns one of ``first_person`` / ``team`` / ``third_person`` / ``vague``.
    """
    text = (evidence_text or "").lower()
    if not text.strip():
        return "vague"

    first_person = bool(re.search(r"\b(i|my|me)\b", text))
    team = bool(re.search(r"\b(we|our|us)\b", text))
    third_person = bool(re.search(r"\b(they|them|someone|the team|the company)\b", text))

    if first_person:
        return "first_person"
    if team:
        return "team"
    if third_person:
        return "third_person"
    return "vague"


def complexity_signal(evidence_text: str) -> str:
    """Specificity/depth signal of an answer.

    Counts concrete indicators (length, metrics, code, technical depth) and
    buckets the result into ``high`` / ``medium`` / ``low``.
    """
    text = (evidence_text or "").strip()
    if not text:
        return "low"

    score = 0
    if len(text) >= 200:
        score += 1
    if re.search(r"\d+\s*(%|ms|s|min|gb|mb|tb|qps|rps|req|requests|users|items|rows|nodes|pods|k|m|b|thousand|million|billion)", text):
        score += 1
    if "```" in text or "`" in text:
        score += 1
    if len(text) < 60:
        score -= 1
    if sum(1 for term in _TECH_TERMS if term in text) >= 2:
        score += 1

    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def detect_evidence_contradiction(record: dict, competency_summary: dict) -> bool:
    """True when the record's score conflicts with the competency's prior average.

    Uses the summary *before* this record is folded in, so the delta reflects a
    genuine inconsistency against established evidence.
    """
    summary = (competency_summary or {}).get(record.get("competency", "")) or {}
    prior_count = int(summary.get("evidence_count", 0) or 0)
    if prior_count == 0:
        return False
    prior_avg = float(summary.get("average_score", 0.0) or 0.0)
    return abs(float(record.get("score", 0.0)) - prior_avg) >= CONTRADICTION_DELTA


def annotate_evidence_quality(record: dict, competency_summary: dict) -> dict:
    """Attach the quality block (strength/impact/ownership/complexity/
    contradiction) to an evidence record."""
    score = float(record.get("score", 0.0))
    confidence = float(record.get("confidence", 0.5))
    record["strength"] = compute_evidence_strength(score, confidence)
    record["impact"] = compute_evidence_impact(score, confidence)
    record["ownership"] = ownership_signal(record.get("evidence_text", ""))
    record["complexity"] = complexity_signal(record.get("evidence_text", ""))
    record["contradiction"] = detect_evidence_contradiction(record, competency_summary)
    return record


def build_evidence_records(
    evaluation: dict,
    question: str,
    question_number: int,
    session_id: str,
    question_objective: dict | None = None,
) -> list[dict]:
    """Flatten a scored evaluation into evidence records (one per dimension).

    Dimensions without a ``score`` are skipped. Each record carries its source
    question, competency (the question's target or a ``dim_*`` fallback) and
    the raw strengths/weaknesses for later synthesis.
    """
    question_objective = question_objective or {}
    target_comp = question_objective.get("target_competency", "")

    extracted: list[dict] = []
    for dim, data in (evaluation or {}).items():
        if dim not in _DIMENSION_KEYS:
            continue
        if not isinstance(data, dict):
            continue

        score = data.get("score")
        if score is None:
            continue

        competency = target_comp if target_comp else f"dim_{dim}"
        confidence = float(data.get("confidence", 0.5))

        record = {
            "id": str(uuid4()),
            "session_id": session_id,
            "competency": competency,
            "dimension": dim,
            "score": float(score),
            "confidence": confidence,
            "evidence_text": data.get("evidence", ""),
            "source_question": question,
            "question_number": question_number,
            "strengths": data.get("strengths", []) or [],
            "weaknesses": data.get("weaknesses", []) or [],
        }
        annotate_evidence_quality(record, {})
        extracted.append(record)
    return extracted


def update_evidence_graph(
    current_graph: dict,
    evidence_list: list[dict],
    hypotheses: list[dict],
) -> dict:
    """V5 evidence graph — competency nodes + evidence→hypothesis edges.

    Nodes record per-competency score aggregates; edges link each evidence item
    to every hypothesis it bears on, tagged with relevance weight and whether
    it supports or contradicts the hypothesis direction.
    """
    graph = dict(current_graph) or {"nodes": {}, "edges": {}}
    nodes = dict(graph.get("nodes") or {})
    edges = dict(graph.get("edges") or {})

    for ev in evidence_list:
        comp = ev.get("competency", "")
        if comp:
            node = nodes.get(comp, {"type": "competency", "count": 0, "scores": []})
            node["count"] += 1
            node["scores"].append(ev.get("score", 0.0))
            node["average_score"] = round(sum(node["scores"]) / node["count"], 4)
            nodes[comp] = node

        for hyp in hypotheses:
            relevance = compute_relevance(hyp, ev)
            if relevance < 0.3:
                continue
            edge_id = f"{ev.get('id', '')}->{hyp.get('id', '')}"
            edges[edge_id] = {
                "source": ev.get("id", ""),
                "target": hyp.get("id", ""),
                "weight": round(relevance, 4),
                "support": _supports_hypothesis(
                    hyp.get("direction", "positive"), ev.get("score", 0.0)
                ),
            }

    return {"nodes": nodes, "edges": edges}


def _supports_hypothesis(direction: str, score: float) -> bool:
    """A score above the midpoint supports a positive hypothesis and
    contradicts a negative one."""
    if direction == "negative":
        return score < 5.0
    return score >= 5.0


def update_competency_summary(
    current_summary: dict,
    evidence_list: list[dict],
) -> dict:
    """Fold evidence into the per-competency summary (counts, averages, gaps)."""
    summary = dict(current_summary)

    for ev in evidence_list:
        comp = ev["competency"]
        score = ev["score"]
        confidence = ev["confidence"]
        strength = ev.get("strength", compute_evidence_strength(score, confidence))

        if comp not in summary:
            summary[comp] = {
                "evidence_count": 0,
                "scores": [],
                "average_score": 0.0,
                "average_confidence": 0.0,
                "average_strength": 0.0,
                "latest_score": score,
                "latest_evidence": ev.get("evidence_text", ""),
                "coverage": 0.0,
                "gap": 1.0,
            }

        s = summary[comp]
        s.setdefault("scores", [])
        s["evidence_count"] = int(s.get("evidence_count", 0)) + 1
        s["scores"].append(score)
        s["latest_score"] = score
        s["latest_evidence"] = ev.get("evidence_text", "")
        s["average_score"] = round(sum(s["scores"]) / s["evidence_count"], 2)
        s["average_confidence"] = round(
            (float(s.get("average_confidence", 0.0)) * (s["evidence_count"] - 1) + confidence)
            / s["evidence_count"],
            2,
        )
        s["average_strength"] = round(
            (float(s.get("average_strength", 0.0)) * (s["evidence_count"] - 1) + strength)
            / s["evidence_count"],
            4,
        )

    return summary


async def evidence_extractor_node(state: dict) -> dict:
    """V4 evidence-extraction wrapper (state in → state out) kept so the engine
    imports it unchanged. The evidence DB flush lives in the engine
    (``InterviewEngine._persist_evidence``); this never touches the database.
    """
    evaluation = state.get("unified_evaluation", {})
    if not evaluation:
        logger.warning("No evaluation to extract evidence from")
        return state

    extracted = build_evidence_records(
        evaluation=evaluation,
        question=state.get("current_question", ""),
        question_number=state.get("question_number", 0),
        session_id=state.get("session_id", ""),
        question_objective=state.get("question_objective", {}) or {},
    )

    if not extracted:
        logger.info("No scored dimensions to extract evidence from")
        return state

    # Annotate contradiction against the pre-fold summary so the delta measures
    # a genuine conflict with established evidence, then fold the records in.
    prior_summary = state.get("competency_summary", {})
    for record in extracted:
        annotate_evidence_quality(record, prior_summary)

    competency_summary = update_competency_summary(
        prior_summary, extracted
    )
    evidence_graph = update_evidence_graph(
        state.get("evidence_graph", {}),
        extracted,
        state.get("hypotheses", []),
    )

    existing_evidence = state.get("evidence_store", [])
    existing_evidence.extend(extracted)

    return {
        **state,
        "extracted_evidence": extracted,
        "evidence_store": existing_evidence,
        "competency_summary": competency_summary,
        "hypotheses": state.get("hypotheses", []),
        "evidence_graph": evidence_graph,
    }
