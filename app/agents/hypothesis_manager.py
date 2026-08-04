import logging
import math
import re
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional

from app.graph.interview_state import InterviewState
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY, map_skill_to_competency

logger = logging.getLogger(__name__)

LEARNING_RATE = 0.3
RELEVANCE_THRESHOLD = 0.3
CONFIRM_THRESHOLD = 0.8
REFUTE_THRESHOLD = 0.2
PRIOR_CONFIDENCE = 0.5  # P(hypothesis true) before any evidence (max entropy)
DEEP_PROBE_CONFIRMED_FLOOR = 0.9  # above this, a confirmed hypothesis is settled


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
                    "competency": map_skill_to_competency(s),
                    "statement": f"Candidate has strong {s}",
                    "direction": "positive",
                    "confidence": PRIOR_CONFIDENCE,
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
                    "competency": map_skill_to_competency(w),
                    "statement": f"Candidate is weak in {w}",
                    "direction": "negative",
                    "confidence": PRIOR_CONFIDENCE,
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
                "competency": map_skill_to_competency(kw),
                "statement": f"Candidate has strong {kw} skills for this role",
                "direction": "positive",
                "confidence": PRIOR_CONFIDENCE,
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
                "competency": comp['id'],
                "statement": f"Candidate demonstrates {comp['name']}",
                "direction": "positive",
                "confidence": PRIOR_CONFIDENCE,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "status": "untested",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            })
            added.add(key)

    hypotheses.append({
        "id": str(uuid4()),
        "competency": "behav_communication",
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


def _entropy(p: float) -> float:
    """Shannon entropy (bits) of a Bernoulli posterior with probability p."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def expected_information_gain(hypothesis: dict) -> float:
    """Expected information gain (V1) ≈ current uncertainty of the hypothesis.

    Untested hypotheses sit at the max-entropy prior and score 1.0 (guaranteed
    coverage). Refuted hypotheses never get re-probed (0.0), and confirmed
    hypotheses near-certain (>= DEEP_PROBE_CONFIRMED_FLOOR) are treated as
    settled. Everything else scores by the entropy of its posterior — the more
    uncertain a belief is, the more a question about it is expected to reveal.
    """
    status = hypothesis.get("status", "untested")
    if status == "refuted":
        return 0.0
    if status == "untested":
        return 1.0
    confidence = float(hypothesis.get("confidence", 0.5) or 0.0)
    p = max(0.0, min(1.0, confidence))
    if status == "confirmed" and p >= DEEP_PROBE_CONFIRMED_FLOOR:
        return 0.0
    return round(_entropy(p), 4)


def next_target(hypotheses: list[dict]) -> dict | None:
    """Pick the hypothesis that maximizes expected information gain.

    Generalizes the old tiered rule (untested → most_uncertain → deep_probe):
    untested hypotheses carry max EIG (1.0) so coverage still wins; among
    probed hypotheses the one closest to p=0.5 (max entropy) wins; confirmed
    hypotheses only when nothing more uncertain remains. The returned target
    carries the EIG score plus a human-readable `selection_reason`.
    """
    if not hypotheses:
        return None

    candidates = [h for h in hypotheses if h.get("status") != "refuted"]
    if not candidates:
        return None

    # max() keeps the first element on ties, so equal-EIG hypotheses (e.g. all
    # untested at 1.0) preserve list order — untested coverage stays stable.
    best = max(candidates, key=expected_information_gain)
    best_score = expected_information_gain(best)

    if best_score > 0.0:
        result = dict(best)
        result["selection_reason"] = (
            "untested" if best.get("status") == "untested" else "max_information_gain"
        )
    else:
        # Nothing productive remains (everything settled or degenerate) — keep
        # the legacy deep-probe behavior: drill into the strongest hypothesis.
        result = dict(max(candidates, key=lambda h: (h.get("confidence", 0.0) or 0.0)))
        result["selection_reason"] = "deep_probe"

    result["information_gain"] = round(best_score, 4)
    return result


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
