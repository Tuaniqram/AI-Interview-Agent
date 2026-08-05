"""V5 hypothesis engine — the Bayesian belief capability.

Owns the prior, the single likelihood-ratio posterior step, relevance scoring
and hypothesis seeding. Pure and stateless: it consumes hypothesis/evidence
dicts and returns updated dicts; the engine decides when to call it and how the
results are committed to the ``InterviewBrain``.

Target selection (``expected_information_gain`` / ``next_target``) lives in
``information_gain.py``; this module re-exports them for convenience.
"""
import logging
import re
from datetime import datetime, timezone
from uuid import uuid4

from app.data.competency_taxonomy import COMPETENCY_TAXONOMY, map_skill_to_competency
from app.agents.reasoning.information_gain import (
    DEEP_PROBE_CONFIRMED_FLOOR,
    _entropy,
    expected_information_gain,
    next_target,
)

logger = logging.getLogger(__name__)

RELEVANCE_THRESHOLD = 0.3
CONFIRM_THRESHOLD = 0.8
REFUTE_THRESHOLD = 0.2
PRIOR_CONFIDENCE = 0.5  # P(hypothesis true) before any evidence (max entropy)

# Likelihood-ratio bounds keep the Bayesian step from going fully certain on
# a single piece of evidence (real posterior uncertainty is never 0/1).
_LR_MIN = 0.05
_LR_MAX = 0.95

__all__ = [
    "RELEVANCE_THRESHOLD",
    "CONFIRM_THRESHOLD",
    "REFUTE_THRESHOLD",
    "PRIOR_CONFIDENCE",
    "DEEP_PROBE_CONFIRMED_FLOOR",
    "_LR_MIN",
    "_LR_MAX",
    "generate_initial_hypotheses",
    "update_hypotheses",
    "bayesian_update",
    "_evidence_support",
    "_posterior",
    "_entropy",
    "expected_information_gain",
    "next_target",
    "compute_relevance",
    "_extract_keywords",
    "hypothesis_node",
]


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
                    "probability": PRIOR_CONFIDENCE,
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
                    "probability": PRIOR_CONFIDENCE,
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
                "probability": PRIOR_CONFIDENCE,
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
                "probability": PRIOR_CONFIDENCE,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "status": "untested",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            })
            added.add(key)

    communication = {
        "id": str(uuid4()),
        "competency": "behav_communication",
        "statement": "Candidate communicates clearly and effectively",
        "direction": "positive",
        "confidence": PRIOR_CONFIDENCE,
        "probability": PRIOR_CONFIDENCE,
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "status": "untested",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    if max_hypotheses <= 0:
        return []
    if len(hypotheses) < max_hypotheses:
        hypotheses.append(communication)
    else:
        # Communication is always probed — reserve one slot for it even when
        # the source material already fills the cap (fixes the prior slice
        # silently dropping the hypothesis at the default cap of 6).
        hypotheses = hypotheses[: max_hypotheses - 1] + [communication]
    return hypotheses


def update_hypotheses(
    hypotheses: list[dict],
    evidence_list: list[dict],
) -> list[dict]:
    """Update hypotheses with evidence using a single Bayesian step.

    ``probability`` is the canonical belief (likelihood-ratio posterior);
    ``confidence`` mirrors it so every legacy reader (``expected_information_gain``,
    ``next_target``, ``should_skip_llm_governor``) sees the same value. The old
    dual delta+Bayesian path has been removed — evidence is applied exactly once.
    """
    hypotheses = [dict(h) for h in hypotheses]

    for evidence in evidence_list:
        ev_score = evidence.get("score", 5.0)
        ev_id = evidence.get("id", "")

        for hypothesis in hypotheses:
            relevance = compute_relevance(hypothesis, evidence)
            if relevance < RELEVANCE_THRESHOLD:
                continue

            prior = float(
                hypothesis.get("probability", hypothesis.get("confidence", PRIOR_CONFIDENCE))
            )
            normalized_score = ev_score / 10.0
            posterior = _posterior(
                prior,
                _evidence_support(normalized_score, hypothesis["direction"]),
                relevance,
            )
            hypothesis["probability"] = round(posterior, 4)
            hypothesis["confidence"] = round(posterior, 4)

            if hypothesis["confidence"] >= CONFIRM_THRESHOLD:
                hypothesis["status"] = "confirmed"
            elif hypothesis["status"] == "untested" and abs(posterior - prior) > 0.01:
                hypothesis["status"] = "testing"
            elif hypothesis["status"] == "testing":
                contradicting_count = len(hypothesis.get("contradicting_evidence", []))
                if (
                    hypothesis["confidence"] <= REFUTE_THRESHOLD
                    or contradicting_count >= 2
                ):
                    hypothesis["status"] = "refuted"

            if ev_id:
                bucket = (
                    "supporting_evidence" if posterior >= prior else "contradicting_evidence"
                )
                if ev_id not in hypothesis.setdefault(bucket, []):
                    hypothesis[bucket].append(ev_id)

            hypothesis["last_updated"] = datetime.now(timezone.utc).isoformat()

    return hypotheses


def bayesian_update(hypothesis: dict, evidence: dict) -> dict:
    """Update one hypothesis from one evidence record using a single
    likelihood-ratio Bayesian step.

    Mirrors ``probability`` back into ``confidence`` so the result is a fully
    Bayesian hypothesis object. Prefer this for new V5 code; ``update_hypotheses``
    keeps the legacy delta semantics and only writes ``probability``.
    """
    h = dict(hypothesis)
    relevance = compute_relevance(h, evidence)
    if relevance < RELEVANCE_THRESHOLD:
        return h

    prior = float(h.get("probability", h.get("confidence", PRIOR_CONFIDENCE)))
    normalized_score = float(evidence.get("score", 5.0)) / 10.0
    posterior = _posterior(prior, _evidence_support(normalized_score, h.get("direction", "positive")), relevance)

    h["probability"] = round(posterior, 4)
    h["confidence"] = round(posterior, 4)
    h["last_updated"] = datetime.now(timezone.utc).isoformat()

    if h["confidence"] >= CONFIRM_THRESHOLD:
        h["status"] = "confirmed"
    elif h["confidence"] <= REFUTE_THRESHOLD and h["status"] not in ("untested",):
        h["status"] = "refuted"
    elif h["status"] == "untested" and abs(posterior - prior) > 0.01:
        h["status"] = "testing"

    ev_id = evidence.get("id", "")
    if ev_id:
        target = "supporting_evidence" if posterior >= prior else "contradicting_evidence"
        bucket = h.setdefault(target, [])
        if ev_id not in bucket:
            bucket.append(ev_id)
    return h


def _evidence_support(normalized_score: float, direction: str) -> float:
    """Map a normalized 0..1 evidence score onto the 0..1 evidence likelihood
    that the hypothesis is true, per its direction."""
    if direction == "positive":
        raw = normalized_score
    else:
        raw = 1 - normalized_score
    return _LR_MIN + (_LR_MAX - _LR_MIN) * max(0.0, min(1.0, raw))


def _posterior(prior: float, support: float, relevance: float) -> float:
    """Bayesian posterior P(H|E) via a likelihood-ratio update.

    ``support`` approximates P(E|H); ``relevance`` attenuates the evidence's
    information content when it only weakly bears on the hypothesis.
    """
    p = max(1e-6, min(1 - 1e-6, float(prior)))
    s = max(_LR_MIN, min(_LR_MAX, float(support)))
    lr = s / (1 - s)
    odds = (p / (1 - p)) * (lr ** relevance)
    return odds / (1 + odds)


def compute_relevance(
    hypothesis: dict,
    evidence: dict,
) -> float:
    """Shared relevance of an evidence record to a hypothesis (0..1).

    Single implementation used by the hypothesis updater, the Bayesian step and
    the evidence graph edge builder (previously duplicated as
    ``_relevance_to_hypothesis`` in the evidence extractor).
    """
    statement = hypothesis.get("statement", "").lower()
    competency = evidence.get("competency", "")
    dimension = evidence.get("dimension", "")
    evidence_text = evidence.get("evidence_text", "")

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


async def hypothesis_node(state: dict) -> dict:
    """V4 hypothesis-node wrapper (state in → state out) kept so the engine
    imports it unchanged; all math lives in this capability module."""
    hypotheses = state.get("hypotheses", [])
    session_id = state.get("session_id", "")
    candidate_profile = state.get("candidate_profile", {})
    job_role = state.get("job_role", "Unknown")
    extracted_evidence = state.get("extracted_evidence", [])
    competency_summary = state.get("competency_summary", {})
    required_competencies = state.get("required_competencies", [])

    if not hypotheses:
        initial = state.get("initial_hypotheses") or []
        if initial:
            hypotheses = [dict(h) for h in initial]
        else:
            hypotheses = generate_initial_hypotheses(
                job_role,
                candidate_profile,
                competency_taxonomy=state.get("competency_taxonomy"),
            )

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
