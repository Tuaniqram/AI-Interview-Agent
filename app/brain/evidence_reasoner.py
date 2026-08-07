"""Evidence Reasoner V5 — proof vs claims.

Turns raw evidence records into a TYPED evidence graph:

    Evidence_001 --supports--> tech_event_driven --required_for--> Senior Backend
    Evidence_001 --(confidence=0.6)--> Claim("understands Kafka")

and classifies every claim as ``mentioned`` / ``demonstrated`` / ``proven`` so
the brain never trusts a claim without evidence. Deterministic; reuses the
V4 ownership/complexity signal extractors.
"""
import logging
import uuid

from app.agents.reasoning.evidence_engine import (
    complexity_signal,
    ownership_signal,
)

logger = logging.getLogger(__name__)

_OWNERSHIP_WORDS = ("design", "architecture", "owned", "architected", "led", "drove", "built the system")
_PROVEN_METRIC_RE = r"\d+\s*(%|ms|s\b|qps|rps|req|users|requests|gb|tb|million|billion|k\b|m\b)"


def classify_claim(record: dict) -> str:
    """mentioned / demonstrated / proven for an evidence record.

    * ``proven``      — first-person ownership + high complexity (concrete
                        metrics, code, multi-topic depth)
    * ``demonstrated`` — first-person/team ownership + medium+ depth
    * ``mentioned``   — anything else (named the tech, explained nothing)
    """
    ownership = record.get("ownership") or ownership_signal(record.get("evidence_text", ""))
    complexity = record.get("complexity") or complexity_signal(record.get("evidence_text", ""))
    text = (record.get("evidence_text") or "").lower()
    import re

    if ownership == "first_person" and complexity == "high":
        return "proven"
    if ownership in ("first_person", "team") and complexity in ("high", "medium"):
        return "demonstrated"
    if ownership == "third_person":
        return "mentioned"
    return "mentioned"


def evidence_to_graph(
    evidence_records: list[dict],
    competency_graph: dict | None = None,
    role_brain: dict | None = None,
) -> dict:
    """Typed evidence graph: evidence -> competency (supports/required_for)
    plus claim confidence edges.

    Every evidence node links to its competency node with ``relation``
    ``supports`` (score >= midpoint) or ``contradicts`` and to the role with
    ``required_for``. Claim confidence is the record's confidence tempered by
    the claim classification.
    """
    graph = {"nodes": {}, "edges": []}
    graph_comp = (competency_graph or {}).get("nodes") or {}
    role = (role_brain or {}).get("role") or ""
    role_class = (role_brain or {}).get("class") or ""

    for ev in evidence_records or []:
        ev_id = ev.get("id") or str(uuid.uuid4())
        comp = ev.get("competency") or ""
        score = float(ev.get("score", 0.0))
        confidence = float(ev.get("confidence", 0.5))
        claim_type = classify_claim(ev)
        claim_confidence = round(
            max(0.1, min(1.0, confidence * {"proven": 1.0, "demonstrated": 0.75, "mentioned": 0.45}[claim_type])),
            4,
        )
        graph["nodes"][ev_id] = {
            "id": ev_id,
            "type": "evidence",
            "claim_type": claim_type,
            "confidence": claim_confidence,
            "question_number": ev.get("question_number"),
        }
        if comp:
            relation = "supports" if score >= 5.0 else "contradicts"
            graph["edges"].append(
                {
                    "source": ev_id,
                    "target": comp,
                    "relation": relation,
                    "weight": round(score / 10.0, 4),
                    "confidence": claim_confidence,
                }
            )
        if role and role_class:
            graph["edges"].append(
                {
                    "source": ev_id,
                    "target": f"role:{role_class}",
                    "relation": "required_for",
                    "weight": round(claim_confidence, 4),
                }
            )

    if role and role_class:
        graph["nodes"][f"role:{role_class}"] = {
            "id": f"role:{role_class}",
            "type": "role",
            "name": role,
        }
    return graph


def evidence_summary_stats(evidence_records: list[dict]) -> dict:
    records = evidence_records or []
    types = {}
    for ev in records:
        t = classify_claim(ev)
        types[t] = types.get(t, 0) + 1
    return {
        "total": len(records),
        "proven": types.get("proven", 0),
        "demonstrated": types.get("demonstrated", 0),
        "mentioned": types.get("mentioned", 0),
        "proof_ratio": round((types.get("proven", 0) + 0.5 * types.get("demonstrated", 0)) / max(1, len(records)), 4),
    }


def evidence_cursor(graph: dict | None) -> dict:
    """T1.3: typed-graph targeting cursor — which competencies still need proof.

    Walks the typed evidence edges (evidence → competency) and flags, per
    competency:
        * ``contradicted`` — at least one ``contradicts`` edge (re-verify!)
        * ``demonstrated`` — evidence exists but nothing classified ``proven``
                              (claims/team-work owned, not first-person+high-depth)
        * ``claimed``      — at least one ``mentioned`` (named but unexplained)
    The director uses these flags to pick challenge/deep-probe modes instead of
    topic rotation, so the typed graph actually steers the conversation.
    """
    graph = graph or {}
    edges = graph.get("edges") or []
    nodes = graph.get("nodes") or {}

    contradicted: list[str] = []
    demonstrated: list[str] = []
    claimed: list[str] = []
    seen_competencies: set[str] = set()

    for edge in edges:
        if edge.get("relation") not in ("supports", "contradicts"):
            continue
        competency = edge.get("target") or ""
        if not competency or competency in seen_competencies:
            continue
        seen_competencies.add(competency)
        if edge.get("relation") == "contradicts":
            contradicted.append(competency)
            continue
        source = nodes.get(edge.get("source") or "") or {}
        claim_type = source.get("claim_type") or "mentioned"
        if claim_type == "mentioned":
            claimed.append(competency)
        elif claim_type in ("demonstrated", "proven"):
            demonstrated.append(competency)

    # Sort by priority within each bucket (most questionable first is stable
    # and deterministic for both the director and the planner).
    return {
        "contradicted": sorted(contradicted),
        "demonstrated": sorted(demonstrated),
        "claimed": sorted(claimed),
    }