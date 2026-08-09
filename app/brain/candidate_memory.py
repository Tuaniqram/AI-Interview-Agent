"""Candidate Memory V5 — long-term candidate intelligence.

A candidate interviewed last month about database design is easier to assess
today. The memory layer keeps a compact learning record (proven strengths,
weaknesses, risk signals) inside the candidate brain and merges prior memory
into fresh builds so the next interview starts from history instead of zero.

Deterministic; persistence rides the existing candidate-brain snapshot tables.
"""
import logging
import re

logger = logging.getLogger(__name__)

_STOP_TOPIC_WORDS = {
    "about", "able", "across", "also", "approach", "area", "back", "been",
    "being", "best", "came", "case", "cases", "challenging", "company",
    "complex", "confidence", "deep", "domain", "during", "even", "every",
    "field", "focus", "getting", "good", "hand", "hard", "having", "high",
    "highly", "including", "into", "large", "learned", "less", "level",
    "limited", "long", "made", "main", "many", "more", "most", "much",
    "need", "needed", "often", "one", "over", "past", "people", "prior",
    "problem", "problems", "rather", "really", "related", "role", "round",
    "show", "showed", "sign", "significant", "skills", "solid", "specific",
    "still", "strong", "stronger", "strongest", "take", "team", "things",
    "time", "took", "use", "used", "using", "very", "weak", "weakness",
    "weaknesses", "well", "when", "where", "which", "while", "worked",
}


def _topic_words(text) -> set[str]:
    """Content words of a strength/weakness phrase, minus filler."""
    if not text:
        return set()
    words = re.findall(r"[a-z][a-z'-]{2,}", str(text).lower())
    return {w for w in words if w not in _STOP_TOPIC_WORDS}


def build_candidate_memory(
    *,
    candidate_id: str = "",
    candidate_brain: dict | None = None,
    candidate_assessment: dict | None = None,
    prior_memory: dict | None = None,
) -> dict:
    """Compact memory snapshot for this interview round."""
    brain = candidate_brain or {}
    assessment = candidate_assessment or {}
    prior = prior_memory or {}
    history = list(prior.get("history") or [])

    round_record = {
        "role": brain.get("job_role") or "",
        "strengths": list(brain.get("strengths") or []),
        "weaknesses": list(brain.get("weaknesses") or []),
        "risk_signals": list(assessment.get("risk_signals") or []),
        "gap_areas": list(assessment.get("gap_areas") or []),
    }
    history.append(round_record)
    history = history[-5:]

    return {
        "candidate_id": candidate_id,
        "history": history,
        "learned_strengths": _consolidate(history, "strengths"),
        "learned_weaknesses": _consolidate(history, "weaknesses"),
        "learned_risk_signals": _consolidate(history, "risk_signals"),
        "interview_count": len(history),
    }


def _consolidate(history: list[dict], key: str) -> list[str]:
    """Consolidate a signal (strengths / weaknesses / risk) across rounds.

    B7: the *latest* round is authoritative. Later rounds win the de-dup
    ordering, and an older weakness/risk ages out when a newer round's
    strengths already refute it — a prior "limited testing" weakness must not
    survive a round whose testing answers were the strongest. Absence alone is
    not refutation: items a newer round merely stopped mentioning are kept.
    """
    if not history:
        return []

    newest_strength_by_topic: dict[str, int] = {}
    for idx, record in enumerate(history):
        for s in record.get("strengths") or []:
            for word in _topic_words(s):
                newest_strength_by_topic[word] = idx

    seen: list[str] = []
    for idx in range(len(history) - 1, -1, -1):
        record = history[idx]
        for item in record.get(key) or []:
            item = str(item).strip()
            if not item or item in seen:
                continue
            if key in ("weaknesses", "risk_signals"):
                refuted_by = max(
                    (
                        newest_strength_by_topic[w]
                        for w in _topic_words(item)
                        if w in newest_strength_by_topic
                    ),
                    default=-1,
                )
                if refuted_by > idx:
                    continue
            seen.append(item)
    return seen[:12]


def memory_into_candidate_brain(candidate_brain: dict, memory: dict) -> dict:
    """Attach the memory snapshot to the candidate brain for persistence."""
    brain = dict(candidate_brain or {})
    brain["candidate_memory"] = memory
    return brain


def merge_prior_memory(
    candidate_brain: dict | None,
    prior_brain: dict | None,
) -> dict:
    """Carry a previous round's memory (e.g. from a candidate_brains row)."""
    prior = (prior_brain or {}).get("candidate_memory") or {}
    if not prior:
        return candidate_brain or {}
    brain = dict(candidate_brain or {})
    brain["candidate_memory"] = prior
    return brain