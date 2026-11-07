"""V5 evidence engine — extracting and structuring candidate evidence.

Pure capability that turns an evaluation dict into evidence records and folds
them into the competency summary + evidence graph. It never touches the
database (the engine owns persistence) and never mutates shared state.

Evidence extraction (V5 hardening, plan step 2):
    One scored answer becomes 1–2 evidence records. Each carries the answer's
    COMPETENCY score (competence dimensions only, see
    ``app.agents.evaluation.scoring.competency_score``) — taking the top-scoring
    dimension made a fluent answer's communication/confidence score count as
    technical evidence. Claims are extracted deterministically from the primary
    competence dimension's quote (no extra LLM call); an answer with nothing
    quotable still yields one record so its score is never dropped.

Evidence quality signals computed per record:
    confidence   — the LLM's stated confidence in the dimension score
    strength     — score magnitude tempered by confidence (0..1)
    impact       — how decisive the evidence is (confidence × |score−5|/5)
    ownership    — first-person attribution signal
    complexity   — specificity/depth signal from the raw answer
    contradiction— conflicts with the competency's prior average score
"""
import json
import logging
import re
from pathlib import Path
from uuid import uuid4

from app.agents.reasoning.hypothesis_engine import compute_relevance
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY

_ALIAS_PATH = Path(__file__).resolve().parents[2] / "data" / "competency_aliases.json"


def _load_competency_aliases() -> dict[str, list[str]]:
    try:
        with _ALIAS_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def _normalize_competency_alias(raw_competency: str) -> str:
    if not raw_competency or not isinstance(raw_competency, str):
        return ""
    raw = raw_competency.strip().lower().replace(" ", "_")
    if not raw:
        return ""

    aliases = _load_competency_aliases()
    for canonical, terms in aliases.items():
        candidates = {canonical.lower()} | {t.lower().replace(" ", "_") for t in terms}
        if raw in candidates:
            return canonical

    if raw in {c["id"] for c in COMPETENCY_TAXONOMY}:
        return raw

    return ""

logger = logging.getLogger(__name__)

_DIMENSION_KEYS = {
    "technical",
    "communication",
    "reasoning",
    "behavioral",
    "confidence",
    "completeness",
}

# Deterministic tie-break order for the top dimension (max() keeps the first
# maximal element, so iteration must follow this priority).
_DIMENSION_PRIORITY = (
    "technical",
    "communication",
    "reasoning",
    "behavioral",
    "confidence",
    "completeness",
)

# An answer yields at most this many evidence claims.
MAX_CLAIMS_PER_ANSWER = 2

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
    "MAX_CLAIMS_PER_ANSWER",
    "build_candidate_evidence",
    "build_evidence_records",
    "build_dimension_metrics",
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
    # Ownership and depth describe the ANSWER, not one extracted sentence: a single claim sentence is
    # rarely 200+ characters with a metric and technical terms, so judged alone even an excellent
    # answer almost never reached "high" and nothing was ever "proven". ``answer_evidence_text`` is
    # the full quoted evidence the claim came from (absent on older records: fall back to the claim).
    signal_text = record.get("answer_evidence_text") or record.get("evidence_text", "")
    record["ownership"] = ownership_signal(signal_text)
    record["complexity"] = complexity_signal(signal_text)
    record["contradiction"] = detect_evidence_contradiction(record, competency_summary)
    return record


def _scored_dimensions(evaluation: dict) -> list[tuple[str, dict]]:
    """Scored dimensions in deterministic priority order (tie-break stable)."""
    scored: list[tuple[str, dict]] = []
    for dim in _DIMENSION_PRIORITY:
        data = (evaluation or {}).get(dim)
        if not isinstance(data, dict):
            continue
        if data.get("score") is None:
            continue
        scored.append((dim, data))
    return scored


def _extract_claims(evidence_text: str, max_claims: int = MAX_CLAIMS_PER_ANSWER) -> list[str]:
    """Deterministic claim extraction from an answer's evidence text.

    Splits into sentences and keeps up to ``max_claims`` in reading order,
    preferring sentences that carry first-person verbs, metrics, or technical
    depth (concrete claims beat filler).
    """
    text = (evidence_text or "").strip()
    if not text:
        return []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
    if not sentences:
        return []

    def _sentence_score(s: str) -> int:
        score = 0
        if len(s) >= 60:
            score += 1
        if re.search(r"\d+", s):
            score += 1
        if any(v in s.lower() for v in _FIRST_PERSON_VERBS):
            score += 2
        if sum(1 for term in _TECH_TERMS if term in s.lower()) >= 2:
            score += 1
        return score

    ranked = sorted(
        range(len(sentences)),
        key=lambda i: (_sentence_score(sentences[i]), -i),
        reverse=True,
    )[:max_claims]
    return [sentences[i] for i in sorted(ranked)]


def _competency_for_dimension(
    dimension: str,
    taxonomy: list[dict] | None = None,
) -> str:
    """Map an evaluation dimension to the taxonomy competency that lists it as
    an evidence dimension (Fix 11: fallback so records are never attributed to
    bare ``dim_*`` nodes when the question objective is missing).

    Prefers an explicit id/name match (``behav_communication`` ↔ communication)
    so generic dimensions like ``communication`` land on the behavioral
    competency named after them rather than the first taxonomy entry that
    happens to list the dimension.
    """
    comps = (taxonomy if taxonomy is not None else COMPETENCY_TAXONOMY)
    dimension_l = dimension.lower()
    for comp in comps:
        if comp.get("id", "").lower() == f"behav_{dimension_l}":
            return comp["id"]
        if dimension_l in (comp.get("name") or "").lower():
            return comp["id"]
    for comp in comps:
        if dimension in (comp.get("evidence_dimensions") or []):
            return comp["id"]
    return ""


def build_candidate_evidence(
    evaluation: dict,
    question: str,
    question_number: int,
    session_id: str,
    question_objective: dict | None = None,
    competency_taxonomy: list[dict] | None = None,
    answer_text: str | None = None,
) -> list[dict]:
    """Turn a scored evaluation into 1–2 evidence records (V5, plan step 2).

    Every record carries the answer's competency score (``scoring.competency_score``: the competence
    dimensions only, never communication/confidence), the primary competence dimension, every
    dimension's score (``dimension_scores``), the source question and the competency (the question's
    target, else the dimension's taxonomy competency — bare ``dim_*`` attributions are never produced).
    Claim sentences come from the primary dimension's quote. An answer with nothing quotable still
    yields one record, built from ``answer_text`` and marked ``quote_missing``, so its score counts.
    Returns ``[]`` only when nothing was scored.
    """
    question_objective = question_objective or {}
    raw_target = str(question_objective.get("target_competency", "") or "")
    # The session's own taxonomy ids are canonical — never relabel them through
    # the alias map (e.g. ``communication`` -> ``behav_communication`` or
    # ``system_design`` -> ``exp_project_depth`` would evict evidence from the
    # required set and starve coverage). Alias normalization only applies to
    # free-text targets that are not already ids in the session's set.
    session_taxonomy = competency_taxonomy or COMPETENCY_TAXONOMY
    session_ids = {
        c.get("id")
        for c in session_taxonomy
        if isinstance(c, dict) and c.get("id")
    }
    if raw_target:
        if raw_target in session_ids:
            target_comp = raw_target
        else:
            normalized_target = _normalize_competency_alias(raw_target)
            target_comp = normalized_target if normalized_target else raw_target
    else:
        target_comp = ""

    scored = _scored_dimensions(evaluation)
    if not scored:
        return []

    top_dim, top_data = max(scored, key=lambda pair: pair[1].get("score", 0.0) or 0.0)
    competency = target_comp or _competency_for_dimension(top_dim, competency_taxonomy)

    logger.debug(
        f"[COMPETENCY_MAPPING] question_competency={raw_target} resolved_competency={competency}"
    )

    if not competency:
        # Defensive fallback: try to fall back to the taxonomy's first competency
        # so we do not drop evidence when mapping fails. This preserves progress
        # even when the question objective was empty or aliases miss.
        taxonomy = competency_taxonomy or COMPETENCY_TAXONOMY
        if taxonomy and isinstance(taxonomy, list) and len(taxonomy) > 0:
            competency = taxonomy[0].get("id")
            logger.warning(
                f"Evidence mapping fallback: assigned top-dimension {top_dim!r} to taxonomy[{competency!r}]"
            )
        else:
            logger.info(
                f"Evidence skipped: top dimension {top_dim!r} has no competency "
                f"mapping and the question objective carried no target"
            )
            return []

    # Plan step 2 (P1): the record carries the answer's COMPETENCY score (competence dimensions only,
    # see ``scoring.competency_score``), not the top dimension's score — delivery dimensions such as
    # communication/confidence used to become technical evidence.
    from app.agents.evaluation.scoring import competency_score, primary_competency_dimension
    from app.data.rubrics import category_from_taxonomy

    category = category_from_taxonomy(competency_taxonomy, competency)
    score = competency_score(evaluation, category)
    if score is None:
        score = float(top_data.get("score", 0.0))
    primary_dim = primary_competency_dimension(evaluation, category) or top_dim
    primary_data = evaluation.get(primary_dim) if isinstance(evaluation.get(primary_dim), dict) else top_data
    confidence = float(primary_data.get("confidence", top_data.get("confidence", 0.5)) or 0.5)
    dimension_scores = {dim: float(data.get("score")) for dim, data in scored}

    # Claims come from the primary dimension's quote, else the top dimension's, else any quote.
    quote_sources = [primary_data, top_data] + [data for _, data in scored]
    answer_evidence, claims = "", []
    for data in quote_sources:
        text = str((data or {}).get("evidence", "") or "")
        found = _extract_claims(text)
        if found:
            answer_evidence, claims = text, found
            break

    # Every scored answer counts (P1 link 4): with nothing quotable, the answer itself is the evidence.
    # Before, such answers — mostly weak ones — produced no record and their low score vanished.
    quote_missing = not claims
    if quote_missing:
        fallback = re.sub(r"\s+", " ", str(answer_text or "")).strip()[:300]
        if not fallback:
            fallback = str(question or "").strip()[:300] or "(no answer text)"
        answer_evidence, claims = fallback, [fallback]

    extracted: list[dict] = []
    for claim in claims:
        record = {
            "id": str(uuid4()),
            "session_id": session_id,
            "competency": competency,
            "dimension": primary_dim,
            "score": float(score),
            "confidence": confidence,
            "evidence_text": claim,
            "answer_evidence_text": answer_evidence,
            "source_question": question,
            "question_number": question_number,
            "strengths": primary_data.get("strengths", []) or [],
            "weaknesses": primary_data.get("weaknesses", []) or [],
            "dimension_scores": dimension_scores,
            "quote_missing": quote_missing,
        }
        annotate_evidence_quality(record, {})
        extracted.append(record)
    return extracted


def build_evidence_records(
    evaluation: dict,
    question: str,
    question_number: int,
    session_id: str,
    question_objective: dict | None = None,
    competency_taxonomy: list[dict] | None = None,
) -> list[dict]:
    """Backwards-compatible alias of :func:`build_candidate_evidence`."""
    return build_candidate_evidence(
        evaluation=evaluation,
        question=question,
        question_number=question_number,
        session_id=session_id,
        question_objective=question_objective,
        competency_taxonomy=competency_taxonomy,
    )


def build_dimension_metrics(
    evaluation: dict,
    top_dimension: str | None,
    claims_extracted: int,
) -> dict:
    """Per-question dimension metrics history (V5 diagnostic record).

    Captures every scored dimension so later stages (challenge, verify,
    final synthesis) can reason about breadth/depth per question without
    re-reading raw evaluations.
    """
    dimensions: dict[str, dict] = {}
    for dim, data in _scored_dimensions(evaluation):
        dimensions[dim] = {
            "score": float(data.get("score", 0.0)),
            "confidence": float(data.get("confidence", 0.5)),
            "has_evidence": bool(data.get("evidence", "")),
        }
    return {
        "top_dimension": top_dimension,
        "claims_extracted": claims_extracted,
        "dimensions": dimensions,
    }


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


# Plan step 2: a positive hypothesis ("candidate demonstrates X") is supported only by evidence at or
# above the hire bar and contradicted only below the weak bar; in between the evidence is neutral.
# The old single 5.0 midpoint let nearly every hypothesis confirm on inflated scores.
SUPPORT_SCORE = 6.5
CONTRADICT_SCORE = 4.5


def _supports_hypothesis(direction: str, score: float) -> bool | None:
    """True/False when the evidence supports/contradicts the hypothesis, ``None`` when neutral."""
    score = float(score or 0.0)
    if score >= SUPPORT_SCORE:
        supports = True
    elif score < CONTRADICT_SCORE:
        supports = False
    else:
        return None
    return supports if direction != "negative" else not supports


def update_competency_summary(
    current_summary: dict,
    evidence_list: list[dict],
    min_evidence_map: dict[str, int] | None = None,
) -> dict:
    """Fold evidence into the per-competency summary (counts, averages, gaps).

    ``gap``/``coverage`` are recomputed from the evidence count against the
    competency's required minimum (``min_evidence_map`` or 2) on every fold —
    previously ``gap`` stayed at its 1.0 default, which froze coverage at 0 and
    made sufficiency unreachable.
    """
    min_evidence_map = min_evidence_map or {}
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

        min_required = int(min_evidence_map.get(comp) or 2)
        if min_required > 0:
            coverage = min(s["evidence_count"] / min_required, 1.0)
        else:
            coverage = 1.0
        s["coverage"] = round(coverage, 2)
        s["gap"] = round(1.0 - coverage, 2)

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

    scored = _scored_dimensions(evaluation)
    dimension_metrics = list(state.get("dimension_metrics", []))
    if not scored:
        logger.info("No scored dimensions to extract evidence from")
        return {**state, "dimension_metrics": dimension_metrics}

    extracted = build_candidate_evidence(
        evaluation=evaluation,
        question=state.get("current_question", ""),
        question_number=state.get("question_number", 0),
        session_id=state.get("session_id", ""),
        question_objective=state.get("question_objective", {}) or {},
        competency_taxonomy=state.get("competency_taxonomy"),
        answer_text=state.get("candidate_answer", ""),
    )
    top_dim = max(scored, key=lambda pair: pair[1].get("score", 0.0) or 0.0)[0]
    dimension_metrics.append(
        build_dimension_metrics(
            evaluation, top_dim, sum(1 for ev in extracted if not ev.get("quote_missing"))
        )
    )

    if not extracted:
        logger.info("No claims extracted from the top-scoring dimension")
        return {**state, "dimension_metrics": dimension_metrics}

    # Annotate contradiction against the pre-fold summary so the delta measures
    # a genuine conflict with established evidence, then fold the records in.
    prior_summary = state.get("competency_summary", {})
    for record in extracted:
        annotate_evidence_quality(record, prior_summary)

    min_evidence_map = {}
    for comp in (state.get("competency_taxonomy") or []):
        if isinstance(comp, dict) and comp.get("id"):
            min_evidence_map[comp["id"]] = int(
                comp.get("default_min_evidence") or 2
            )

    competency_summary = update_competency_summary(
        prior_summary, extracted, min_evidence_map=min_evidence_map
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
        "dimension_metrics": dimension_metrics,
    }
