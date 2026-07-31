import logging
import re
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional

from app.graph.interview_state import InterviewState
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY, SKILL_TO_COMPETENCY

logger = logging.getLogger(__name__)

LEARNING_RATE = 0.3
RELEVANCE_THRESHOLD = 0.3
CONFIRM_THRESHOLD = 0.8
REFUTE_THRESHOLD = 0.2


def generate_initial_hypotheses(
    job_role: str,
    candidate_profile: dict | None = None,
    max_hypotheses: int = 6,
    competency_taxonomy: list[dict] | None = None,
) -> list[dict]:
    hypotheses = []
    added = set()
    session_id = ""  # filled by caller

    if candidate_profile:
        strengths = candidate_profile.get("strengths", [])
        weaknesses = candidate_profile.get("weaknesses", [])

        for s in strengths[:3]:
            key = f"strong_{s.lower().replace(' ', '_')[:20]}"
            if key not in added:
                hypotheses.append({
                    "id": str(uuid4()),
                    "statement": f"Candidate has strong {s}",
                    "direction": "positive",
                    "confidence": 0.0,
                    "supporting_evidence": [],
                    "contradicting_evidence": [],
                    "status": "untested",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                })
                added.add(key)

        for w in weaknesses[:3]:
            key = f"weak_{w.lower().replace(' ', '_')[:20]}"
            if key not in added:
                hypotheses.append({
                    "id": str(uuid4()),
                    "statement": f"Candidate is weak in {w}",
                    "direction": "negative",
                    "confidence": 0.0,
                    "supporting_evidence": [],
                    "contradicting_evidence": [],
                    "status": "untested",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                })
                added.add(key)

    role_keywords = _extract_keywords(job_role)
    for kw in role_keywords[:3]:
        key = f"role_{kw.lower().replace(' ', '_')[:20]}"
        if key not in added:
            hypotheses.append({
                "id": str(uuid4()),
                "statement": f"Candidate has strong {kw} skills for this role",
                "direction": "positive",
                "confidence": 0.0,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "status": "untested",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            })
            added.add(key)

    taxonomy = competency_taxonomy or COMPETENCY_TAXONOMY
    for comp in taxonomy[:3]:
        key = f"comp_{comp['id']}"
        if key not in added:
            hypotheses.append({
                "id": str(uuid4()),
                "statement": f"Candidate demonstrates {comp['name']}",
                "direction": "positive",
                "confidence": 0.0,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "status": "untested",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            })
            added.add(key)

    hypotheses.append({
        "id": str(uuid4()),
        "statement": "Candidate communicates clearly and effectively",
        "direction": "positive",
        "confidence": 0.0,
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "status": "untested",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    })

    return hypotheses[:max_hypotheses]


def update_hypotheses(
    hypotheses: list[dict],
    evidence_list: list[dict],
) -> list[dict]:
    hypotheses = [dict(h) for h in hypotheses]

    for evidence in evidence_list:
        ev_score = evidence.get("score", 5.0)
        ev_text = evidence.get("evidence_text", "")
        ev_comp = evidence.get("competency", "")
        ev_dim = evidence.get("dimension", "")
        ev_id = evidence.get("id", "")

        for hypothesis in hypotheses:
            relevance = _compute_relevance(hypothesis, ev_comp, ev_dim, ev_text)
            if relevance < RELEVANCE_THRESHOLD:
                continue

            normalized_score = ev_score / 10.0
            delta = (normalized_score - 0.5) * 2 * relevance * LEARNING_RATE

            if hypothesis["direction"] == "positive":
                hypothesis["confidence"] += delta
            else:
                hypothesis["confidence"] -= delta

            hypothesis["confidence"] = max(0.0, min(1.0, hypothesis["confidence"]))

            if delta > 0:
                if ev_id not in hypothesis["supporting_evidence"]:
                    hypothesis["supporting_evidence"].append(ev_id)
            else:
                if ev_id not in hypothesis["contradicting_evidence"]:
                    hypothesis["contradicting_evidence"].append(ev_id)

            if hypothesis["confidence"] >= CONFIRM_THRESHOLD:
                hypothesis["status"] = "confirmed"
            elif hypothesis["status"] == "untested" and abs(delta) > 0.01:
                hypothesis["status"] = "testing"
            elif hypothesis["status"] == "testing":
                contradicting_count = len(hypothesis.get("contradicting_evidence", []))
                if contradicting_count >= 2 or (
                    contradicting_count >= 1 and hypothesis["confidence"] <= REFUTE_THRESHOLD
                ):
                    hypothesis["status"] = "refuted"

            hypothesis["last_updated"] = datetime.now(timezone.utc).isoformat()

    return hypotheses


def next_target(hypotheses: list[dict]) -> dict | None:
    if not hypotheses:
        return None

    untested = [h for h in hypotheses if h["status"] == "untested"]
    if untested:
        result = dict(untested[0])
        result["selection_reason"] = "untested"
        return result

    testing = [h for h in hypotheses if h["status"] == "testing"]
    if testing:
        result = dict(min(testing, key=lambda h: abs(h["confidence"] - 0.5)))
        result["selection_reason"] = "most_uncertain"
        return result

    confirmed = [h for h in hypotheses if h["status"] == "confirmed"]
    if confirmed:
        result = dict(max(confirmed, key=lambda h: h["confidence"]))
        result["selection_reason"] = "deep_probe"
        return result

    return None


def _compute_relevance(
    hypothesis: dict,
    competency: str,
    dimension: str,
    evidence_text: str,
) -> float:
    statement = hypothesis.get("statement", "").lower()

    if competency and competency in statement:
        return 0.9
    if dimension and dimension in statement:
        return 0.7

    words = set(re.findall(r'\w+', statement))
    ev_words = set(re.findall(r'\w+', evidence_text.lower()))
    overlap = words & ev_words
    if overlap:
        return min(0.3 + (len(overlap) * 0.1), 0.8)

    return 0.1


def _extract_keywords(job_role: str) -> list[str]:
    if not job_role:
        return []
    stop_words = {"engineer", "developer", "manager", "senior", "junior", "lead", "staff", "principal"}
    words = re.findall(r'\w+', job_role.lower())
    return [w for w in words if w not in stop_words and len(w) > 2]
