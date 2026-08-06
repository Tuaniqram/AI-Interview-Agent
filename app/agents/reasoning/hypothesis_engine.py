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
from app.agents.reasoning.contradiction_engine import (
    MAX_QUESTIONS_PER_COMPETENCY,
    competency_question_counts,
)
from app.agents.reasoning.information_gain import (
    DEEP_PROBE_CONFIRMED_FLOOR,
    _entropy,
    expected_information_gain,
    next_target,
)

logger = logging.getLogger(__name__)

RELEVANCE_THRESHOLD = 0.3
CONFIRM_THRESHOLD = 0.75
REFUTE_THRESHOLD = 0.35
DEFAULT_REQUIRED_EVIDENCE = 3
# A hypothesis probed beyond `required_evidence * SATURATION_LIMIT` pieces of
# evidence without confirming or refuting holds no new information — saturate.
SATURATION_LIMIT = 2
SATURATED_STATUSES = ("confirmed", "refuted", "saturated")
PRIOR_CONFIDENCE = 0.5  # P(hypothesis true) before any evidence (max entropy)

# Likelihood-ratio bounds keep the Bayesian step from going fully certain on
# a single piece of evidence (real posterior uncertainty is never 0/1).
_LR_MIN = 0.05
_LR_MAX = 0.95

# Words too generic to link an evidence claim to a hypothesis (Fix 11: "the"
# shared between a statement and a claim must not move beliefs).
_RELEVANCE_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "in", "on", "to", "for", "with",
    "at", "by", "is", "was", "are", "were", "i", "we", "you", "it", "as",
    "be", "that", "this", "from", "had", "have", "has", "my", "their",
    "our", "his", "her", "they", "them", "me", "not", "but", "so", "if",
    "then", "than", "there", "when", "which", "who", "will", "would",
    "can", "could", "should", "about", "into", "over", "out",
})

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


def _map_to_session_competency(raw: str, taxonomy: list[dict] | None) -> str | None:
    """Resolve a skill-derived competency id onto the session's taxonomy so
    hypotheses live in the same id space as coverage and sufficiency.

    Returns ``None`` when the id (or an alias/name match) is not part of the
    set — off-set hypotheses diluted the required-open/resolved checks and
    never counted toward coverage.
    """
    if not raw:
        return None
    session = taxonomy if taxonomy is not None else COMPETENCY_TAXONOMY
    for c in session:
        if isinstance(c, dict) and c.get("id") == raw:
            return raw
    raw_norm = raw.replace("_", " ").strip().lower()
    if not raw_norm:
        return None
    for c in session:
        if not isinstance(c, dict):
            continue
        name = (c.get("name") or "").strip().lower()
        if name and (raw_norm == name or raw_norm in name or name in raw_norm):
            return c["id"]
    return None


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
            if key in added:
                continue
            session_comp = _map_to_session_competency(
                map_skill_to_competency(s), competency_taxonomy
            )
            if session_comp is None:
                continue
            hypotheses.append({
                "id": str(uuid4()),
                "competency": session_comp,
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
            if key in added:
                continue
            session_comp = _map_to_session_competency(
                map_skill_to_competency(w), competency_taxonomy
            )
            if session_comp is None:
                continue
            hypotheses.append({
                "id": str(uuid4()),
                "competency": session_comp,
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
        if key in added:
            continue
        session_comp = _map_to_session_competency(
            map_skill_to_competency(kw), competency_taxonomy
        )
        if session_comp is None:
            continue
        hypotheses.append({
            "id": str(uuid4()),
            "competency": session_comp,
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

    if max_hypotheses <= 0:
        return []
    communication_comp = _map_to_session_competency(
        "behav_communication", competency_taxonomy
    )
    if not communication_comp:
        return hypotheses
    communication = {
        "id": str(uuid4()),
        "competency": communication_comp,
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

    if len(hypotheses) < max_hypotheses:
        hypotheses.append(communication)
    else:
        # Communication is always probed — reserve one slot for it even when
        # the source material already fills the cap (fixes the prior slice
        # silently dropping the hypothesis at the default cap of 6).
        hypotheses = hypotheses[: max_hypotheses - 1] + [communication]
    return hypotheses


def _required_evidence(hypothesis: dict, required_evidence_map: dict | None = None) -> int:
    """Evidence pieces needed before this hypothesis can be confirmed."""
    explicit = hypothesis.get("required_evidence")
    if explicit:
        return int(explicit)
    if required_evidence_map:
        value = required_evidence_map.get(hypothesis.get("competency", ""))
        if value:
            return int(value)
    return DEFAULT_REQUIRED_EVIDENCE


def attach_evidence_requirements(
    hypotheses: list[dict],
    required_evidence_map: dict | None = None,
) -> list[dict]:
    """Stamp each hypothesis with its per-competency evidence budget.

    Fills ``required_evidence`` (from the intelligence bundle's
    ``evidence_requirements`` or the default) and ``evidence_count`` so every
    consumer sees the full lifecycle fields. Idempotent.
    """
    for h in hypotheses:
        h["required_evidence"] = _required_evidence(h, required_evidence_map)
        h["max_allowed_evidence"] = h["required_evidence"] * SATURATION_LIMIT
        h.setdefault("evidence_count", 0)
    return hypotheses


def _apply_status_transition(
    hypothesis: dict,
    required_evidence: int,
    contradicting_count: int,
    belief_moved: bool,
) -> None:
    """Deterministic lifecycle step after a Bayesian update.

    Order: confirm (evidence + high confidence) → refute (low confidence or
    counter-evidence) → testing (first belief movement) → saturate (probed past
    the budget without a settled belief — no new information left).
    """
    evidence_count = int(hypothesis.get("evidence_count", 0) or 0)
    confidence = float(hypothesis.get("confidence", 0.0) or 0.0)
    status = hypothesis.get("status", "untested")

    # Fix 11: one piece of evidence can never confirm — a single record (even
    # with a low blueprint minimum) is too thin for a hiring belief.
    if evidence_count >= max(required_evidence, 2) and confidence >= CONFIRM_THRESHOLD:
        hypothesis["status"] = "confirmed"
    elif confidence <= REFUTE_THRESHOLD and status != "untested":
        hypothesis["status"] = "refuted"
    elif contradicting_count >= 2 and status == "testing":
        hypothesis["status"] = "refuted"
    elif evidence_count >= required_evidence * SATURATION_LIMIT and status in (
        "untested",
        "testing",
    ):
        hypothesis["status"] = "saturated"
    elif status == "untested" and belief_moved:
        hypothesis["status"] = "testing"


def update_hypotheses(
    hypotheses: list[dict],
    evidence_list: list[dict],
    required_evidence_map: dict | None = None,
) -> list[dict]:
    """Update hypotheses with evidence using a single Bayesian step.

    ``probability`` is the canonical belief (likelihood-ratio posterior);
    ``confidence`` mirrors it so every legacy reader (``expected_information_gain``,
    ``next_target``, ``should_skip_llm_governor``) sees the same value. The old
    dual delta+Bayesian path has been removed — evidence is applied exactly once.

    Lifecycle (AURA hardening): hypotheses confirm only after enough evidence
    (``required_evidence``) AND high confidence; they refute on low confidence
    or two contradicting pieces; they saturate when probed past the budget
    without a settled belief.
    """
    hypotheses = [dict(h) for h in hypotheses]

    for evidence in evidence_list:
        ev_score = evidence.get("score", 5.0)
        ev_id = evidence.get("id", "")

        for hypothesis in hypotheses:
            relevance = compute_relevance(hypothesis, evidence)
            if relevance < RELEVANCE_THRESHOLD:
                continue

            required_evidence = _required_evidence(hypothesis, required_evidence_map)

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
            hypothesis["evidence_count"] = int(hypothesis.get("evidence_count", 0) or 0) + 1

            _apply_status_transition(
                hypothesis,
                required_evidence,
                len(hypothesis.get("contradicting_evidence", [])),
                abs(posterior - prior) > 0.01,
            )

            if ev_id:
                bucket = (
                    "supporting_evidence" if posterior >= prior else "contradicting_evidence"
                )
                if ev_id not in hypothesis.setdefault(bucket, []):
                    hypothesis[bucket].append(ev_id)

            hypothesis["last_updated"] = datetime.now(timezone.utc).isoformat()

    return hypotheses


def bayesian_update(
    hypothesis: dict,
    evidence: dict,
    required_evidence_map: dict | None = None,
) -> dict:
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
    h["evidence_count"] = int(h.get("evidence_count", 0) or 0) + 1
    h["last_updated"] = datetime.now(timezone.utc).isoformat()

    _apply_status_transition(
        h,
        _required_evidence(h, required_evidence_map),
        len(h.get("contradicting_evidence", [])),
        abs(posterior - prior) > 0.01,
    )

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

    # The evidence was collected while probing this exact competency — the
    # strongest relevance signal (fixes hypotheses whose statements carry the
    # competency's display name rather than its id, which never matched the
    # keyword path).
    hyp_competency = hypothesis.get("competency", "")
    if hyp_competency and competency == hyp_competency:
        return 0.85
    if competency and competency in statement:
        return 0.9
    if dimension and dimension in statement:
        return 0.7

    words = set(re.findall(r'\w+', statement))
    ev_words = set(re.findall(r'\w+', evidence_text.lower()))
    overlap = (words & ev_words) - _RELEVANCE_STOPWORDS
    # Fix 11: a single shared word (e.g. "team", "system") is too weak a link —
    # it spread one answer's records across many hypotheses and over-settled
    # them. Require at least two shared content words and cap the overlap
    # contribution below the direct competency/dimension matches (0.7+).
    if len(overlap) >= 2:
        return min(0.3 + (len(overlap) * 0.05), 0.6)

    return 0.1


def _extract_keywords(job_role: str) -> list[str]:
    if not job_role:
        return []
    stop_words = {"engineer", "developer", "manager", "senior", "junior", "lead", "staff", "principal"}
    words = re.findall(r'\w+', job_role.lower())
    return [w for w in words if w not in stop_words and len(w) > 2]


def _requirements_map(state: dict) -> dict[str, int]:
    """Per-competency evidence minimums from the V5 intelligence bundle."""
    req_map: dict[str, int] = {}
    for req in state.get("evidence_requirements") or []:
        if isinstance(req, dict) and req.get("competency"):
            try:
                req_map[str(req["competency"])] = int(req.get("min_evidence") or 0)
            except (TypeError, ValueError):
                continue
    for comp in state.get("competency_taxonomy") or []:
        if isinstance(comp, dict) and comp.get("id") and comp["id"] not in req_map:
            req_map[str(comp["id"])] = int(comp.get("default_min_evidence") or 0)
    return {k: v for k, v in req_map.items() if v > 0}


def _capped_competencies(questions_asked: list) -> set[str]:
    """Competencies that already got their maximum share of questions (Fix 7)."""
    return {
        comp
        for comp, count in competency_question_counts(questions_asked).items()
        if count >= MAX_QUESTIONS_PER_COMPETENCY
    }


def _target_candidates(
    hypotheses: list[dict],
    state: dict,
    capped: set[str],
) -> tuple[list[dict], str | None]:
    """Filter out hypotheses in capped competencies unless that would leave
    nothing to ask (never deadlock the interview). Also drops the planned
    competency from selection when it is capped."""
    if capped:
        filtered = [h for h in hypotheses if h.get("competency") not in capped]
        if filtered:
            planned = state.get("planned_competency")
            if planned in capped:
                planned = None
            return filtered, planned
    return hypotheses, state.get("planned_competency")


def _resolve_target(
    hypotheses: list[dict],
    state: dict,
    candidates: list[dict],
    planned: str | None,
) -> dict | None:
    """Select the next hypothesis to probe — never returning None while a
    competency was planned (Fix 11: a null target caused premature finals).

    ``next_target`` can return None when every candidate is excluded or
    settled; fall back to the planned competency's seed, then to any open
    hypothesis, then to the planned seed itself so the interview always has a
    question to ask (the generator then attributes the question to the
    planned competency instead of emitting a ``dim_*`` record).
    """
    target = next_target(
        candidates,
        exclude_ids=[state.get("last_hypothesis_target_id", "")],
        planned_competency=planned,
        competency_coverage={
            comp: int(s.get("evidence_count", 0) or 0)
            for comp, s in (state.get("competency_summary") or {}).items()
        },
    )
    if target:
        return target
    if planned:
        for h in hypotheses:
            if h.get("competency") == planned and h.get("status") in ("untested", "testing"):
                return h
        for h in hypotheses:
            if h.get("competency") == planned:
                return h
    for h in hypotheses:
        if h.get("status") in ("untested", "testing"):
            return h
    # No open hypotheses — try seeding one for the planned competency if present
    if planned:
        try:
            return _seed_hypothesis_for_competency(
                planned,
                session_id=state.get("session_id", ""),
                competency_taxonomy=state.get("competency_taxonomy"),
            )
        except Exception:
            pass
    # As a last resort, seed for the top taxonomy competency so the planner
    # never returns None while the interview still has question budget.
    taxonomy = state.get("competency_taxonomy") or COMPETENCY_TAXONOMY
    if taxonomy and isinstance(taxonomy, list) and len(taxonomy) > 0:
        try:
            top = taxonomy[0].get("id")
            return _seed_hypothesis_for_competency(
                top,
                session_id=state.get("session_id", ""),
                competency_taxonomy=taxonomy,
            )
        except Exception:
            pass
    return None


async def hypothesis_node(state: dict) -> dict:
    """V4 hypothesis-node wrapper (state in → state out) kept so the engine
    imports it unchanged; all math lives in this capability module."""
    hypotheses = state.get("hypotheses", [])
    session_id = state.get("session_id", "")
    candidate_profile = state.get("candidate_profile", {})
    job_role = state.get("job_role", "Unknown")
    extracted_evidence = state.get("extracted_evidence", [])
    req_map = _requirements_map(state)

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
        attach_evidence_requirements(hypotheses, req_map)

        hypo_state = {}
        for h in hypotheses:
            h["session_id"] = session_id
            h["id"] = h.get("id") or str(uuid4())
            hypo_state[h["id"]] = {"statement": h["statement"], "status": h["status"]}

        planned = state.get("planned_competency")
        if planned:
            open_for_planned = [
                h for h in hypotheses
                if h.get("competency") == planned
                and h.get("status") in ("untested", "testing")
            ]
            if not open_for_planned:
                hypotheses.append(
                    _seed_hypothesis_for_competency(
                        planned,
                        session_id=session_id,
                        competency_taxonomy=state.get("competency_taxonomy"),
                    )
                )
                attach_evidence_requirements(hypotheses[-1:], req_map)

        candidates, planned = _target_candidates(
            hypotheses, state, _capped_competencies(state.get("questions_asked", []))
        )
        target = _resolve_target(hypotheses, state, candidates, planned)

        return {
            **state,
            "hypotheses": hypotheses,
            "hypothesis_state": hypo_state,
            "hypothesis_target": target,
        }

    if extracted_evidence:
        evidence_records = [
            {
                "id": ev.get("id", ""),
                "competency": ev.get("competency", ""),
                "dimension": ev.get("dimension", ""),
                "score": ev.get("score", 0.0),
                "confidence": ev.get("confidence", 0.5),
                "evidence_text": ev.get("evidence_text", ""),
            }
            for ev in extracted_evidence
        ]

        hypotheses = update_hypotheses(hypotheses, evidence_records, required_evidence_map=req_map)

    planned = state.get("planned_competency")
    if planned:
        open_for_planned = [
            h for h in hypotheses
            if h.get("competency") == planned
            and h.get("status") in ("untested", "testing")
        ]
        if not open_for_planned:
            hypotheses.append(
                _seed_hypothesis_for_competency(
                    planned,
                    session_id=session_id,
                    competency_taxonomy=state.get("competency_taxonomy"),
                )
            )
            attach_evidence_requirements(hypotheses[-1:], req_map)

    candidates, planned = _target_candidates(
        hypotheses, state, _capped_competencies(state.get("questions_asked", []))
    )
    target = _resolve_target(hypotheses, state, candidates, planned)

    return {
        **state,
        "hypotheses": hypotheses,
        "hypothesis_target": target,
    }


def _seed_hypothesis_for_competency(
    competency: str,
    session_id: str = "",
    competency_taxonomy: list[dict] | None = None,
) -> dict:
    """Fresh untested hypothesis for a competency the planner just rotated to.

    Used by ``hypothesis_node`` so a competency switch always has an open
    hypothesis to target (the previous one is settled and saturated).
    """
    name = competency
    for comp in (competency_taxonomy or COMPETENCY_TAXONOMY):
        if comp.get("id") == competency:
            name = comp.get("name", competency)
            break
    return {
        "id": str(uuid4()),
        "session_id": session_id,
        "competency": competency,
        "statement": f"Candidate demonstrates {name}",
        "direction": "positive",
        "confidence": PRIOR_CONFIDENCE,
        "probability": PRIOR_CONFIDENCE,
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "status": "untested",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
