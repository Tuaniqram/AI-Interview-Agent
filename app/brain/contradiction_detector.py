"""Contradiction / Challenge Brain V5.

Guards against fake seniority: a candidate who CLAIMS architecture ownership
while the evidence stays thin or contradictory gets flagged, and the question
planner is told to CHALLENGE instead of accepting the claim.

Deterministic; consumes the runtime contradiction list, the typed evidence
graph and the role's seniority floor.
"""
import logging
import re

from app.brain.evidence_reasoner import classify_claim

logger = logging.getLogger(__name__)

_OWNERSHIP_CLAIMS = (
    "design",
    "architecture",
    "architected",
    "owned",
    "led",
    "scal",
    "tradeoff",
    "microservice",
    "event-driven",
    "event driven",
    "kafka",
    "reliab",
    "availability",
)

# "I'd think about scalability" or "I haven't done that before" is not a claim of seniority - a
# candidate who admits a gap must not be pressure-tested as if they had boasted ownership.
_HEDGE_RE = re.compile(
    r"\b(i'?d|i would|would|i might|maybe|probably|perhaps|i think|i guess|haven'?t|have not|never|"
    r"not sure|don'?t know|no experience|not really)\b",
    re.IGNORECASE,
)
_EXPERIENCE_RE = re.compile(
    r"\b(i|we)\s+(?:\w+\s+)?(built|designed|architected|led|owned|scaled|migrated|implemented|introduced|"
    r"reduced|moved|wrote|ran|used|had|shipped|deployed|maintained|managed|created|developed)\b",
    re.IGNORECASE,
)


# Plan step 8 (P6): an ownership claim is a first-person, past-tense statement of having owned the work.
# Topic words ("we used Kafka for reliability") and the "we" form made almost every answer a "claim of
# seniority", which sent hesitant candidates into challenge mode for a whole interview.
_OWNERSHIP_RE = re.compile(r"\bI\s+(?:\w+\s+)?(designed|architected|led|owned|built|drove)\b", re.IGNORECASE)


def _is_ownership_claim(text: str) -> bool:
    """A first-person past-tense ownership statement ("I designed the ledger service")."""
    return bool(_OWNERSHIP_RE.search((text or "").replace("\u2019", "'")))


_SENIORITY_PROBES = [
    "What tradeoff did you make and what did you give up?",
    "Why this design instead of the simpler alternative?",
    "What failed in production and how did you diagnose it?",
    "Who else depended on your design and what did you own end to end?",
]


def seniority_claim_risk(
    evidence_records: list[dict],
    role_brain: dict | None = None,
    contradictions: list | None = None,
    challenged_competencies: list | None = None,
) -> dict:
    """Risk that claimed seniority is not backed by proof.

    Claims ownership in first person while the proof ratio stays low (or contradictions exist) => high
    risk => the planner must challenge. A competency already challenged once is not challenged again
    (plan step 8): its claims stop counting.
    """
    challenged = set(challenged_competencies or [])
    records = [ev for ev in (evidence_records or []) if ev.get("competency") not in challenged]
    claims = []
    for ev in records:
        if _is_ownership_claim(ev.get("evidence_text") or "") and classify_claim(ev) in ("mentioned", "demonstrated"):
            claims.append(ev)
    ownership_claims = len(claims)
    proven = sum(1 for ev in records if classify_claim(ev) == "proven")

    serious = [
        c for c in (contradictions or [])
        if c.get("severity") in ("high", "medium")
    ]
    total = max(1, len(records))
    proof_ratio = proven / total

    if ownership_claims >= 2 and proof_ratio < 0.4:
        level = "high"
    elif ownership_claims >= 2 and len(serious) >= 1:
        level = "high"
    elif ownership_claims >= 1 and proof_ratio < 0.5:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "ownership_claims": ownership_claims,
        "proven_claims": proven,
        "proof_ratio": round(proof_ratio, 4),
        "serious_contradictions": len(serious),
        "probe_questions": _SENIORITY_PROBES if level in ("high", "medium") else [],
        "action": "challenge" if level in ("high", "medium") else "validate",
    }


def build_contradiction_state(
    contradictions: list | None,
    evidence_records: list[dict],
    role_brain: dict | None = None,
    challenged_competencies: list | None = None,
) -> dict:
    """Assemble the contradiction brain section."""
    seniority_risk = seniority_claim_risk(evidence_records, role_brain, contradictions, challenged_competencies)
    return {
        "contradictions": [
            {
                "id": c.get("id") or str(i),
                "severity": c.get("severity", "low"),
                "type": c.get("type", "evidence_conflict"),
                "summary": c.get("summary") or c.get("description") or c.get("statement") or "",
                "statement": c.get("statement") or c.get("summary") or c.get("description") or "",
                "status": c.get("status", "open"),
            }
            for i, c in enumerate(contradictions or [])
        ],
        "seniority_risk": seniority_risk,
        "needs_challenge": seniority_risk.get("action") == "challenge",
    }