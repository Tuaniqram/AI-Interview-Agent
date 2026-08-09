"""Evidence Reading V5 — semantic read of the actual answers.

Turns the LLM's transcript reading into a structured, deterministic
``evidence_reading`` dict that downstream layers consume as *signals*. The LLM
never scores or decides: it classifies each answer's claims and surfaces
off-rubric observations, and the deterministic engine decides what to do with
them.

The downgrade-only rule (:func:`effective_claim`) is the core safety invariant:
the effective claim type is the *weaker* of the semantic and the deterministic
(regex) classification, so the LLM can only confirm or downgrade — never inflate
a claim past what the deterministic signals already support.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

CLAIM_NAMES = ("mentioned", "demonstrated", "proven")
CLAIM_RANK = {"mentioned": 0, "demonstrated": 1, "proven": 2}
SPECIFICITY_LEVELS = ("low", "medium", "high")
OWNERSHIP_LEVELS = ("first_person", "team", "third_person", "vague")

# Review checks produced from the reading are capped below "high" so they can
# flag for review and trim confidence, but can never alone demote a decisive
# verdict (demotion requires a deterministic high-severity check).
MAX_SEMANTIC_SEVERITY = "medium"

MAX_PER_ANSWER = 60
MAX_OFF_RUBRIC_ITEMS = 10
MAX_SEMANTIC_RISKS = 10
MAX_ANSWER_CHARS = 2000
MAX_TRANSCRIPT_ITEMS = 20

_ACCEPTED_KEYS = (
    "claim_classification",
    "verifiable",
    "specificity",
    "ownership",
    "supporting_metric",
    "quote",
)


def _clean(value: Any, allowed: tuple[str, ...], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _text(value: Any, max_len: int = 200) -> str:
    text = str(value or "").strip()
    return text[:max_len]


def effective_claim(semantic: str | None, regex: str | None) -> str:
    """Downgrade-only rule: min(semantic, regex) over mentioned < demonstrated < proven.

    * regex "proven" + semantic "mentioned"  -> "mentioned"  (LLM caught vagueness)
    * regex "proven" + semantic "proven"     -> "proven"     (LLM corroborated)
    * regex "mentioned" + semantic "proven"  -> "mentioned"  (deterministic is the floor)
    """
    sem = _clean(semantic, CLAIM_NAMES, "mentioned")
    rx = _clean(regex, CLAIM_NAMES, "mentioned")
    return min(sem, rx, key=CLAIM_RANK.__getitem__)


def map_evidence_reading(evidence_store: list[dict], llm_output: Any) -> dict:
    """Normalize raw LLM output into a structured ``evidence_reading`` dict.

    Only the fields the prompt declares are accepted; per-answer entries whose
    ``evidence_id`` does not match a real evidence record are dropped, so a
    hallucinated id can never enter the brain. Fully deterministic.
    """
    records = {str(ev.get("id", "")): ev for ev in (evidence_store or [])}
    raw = llm_output if isinstance(llm_output, dict) else {}

    reading: dict[str, Any] = {
        "per_answer": {},
        "off_rubric": {"red_flags": [], "hidden_strengths": []},
        "semantic_risks": [],
    }

    per_answer = raw.get("per_answer") or []
    if isinstance(per_answer, list):
        for item in per_answer[:MAX_PER_ANSWER]:
            if not isinstance(item, dict):
                continue
            ev_id = str(item.get("evidence_id", ""))
            if not ev_id or ev_id not in records:
                continue
            entry = {
                "evidence_id": ev_id,
                "claim_classification": _clean(
                    item.get("claim_classification"), CLAIM_NAMES, "mentioned"
                ),
                "verifiable": bool(item.get("verifiable")),
                "specificity": _clean(item.get("specificity"), SPECIFICITY_LEVELS, "low"),
                "ownership": _clean(item.get("ownership"), OWNERSHIP_LEVELS, "vague"),
                "supporting_metric": _text(item.get("supporting_metric")),
                "quote": _text(item.get("quote"), 300),
            }
            reading["per_answer"][ev_id] = entry

    off_rubric = raw.get("off_rubric")
    if isinstance(off_rubric, dict):
        flags = off_rubric.get("red_flags") if isinstance(off_rubric.get("red_flags"), list) else []
        strengths = (
            off_rubric.get("hidden_strengths")
            if isinstance(off_rubric.get("hidden_strengths"), list)
            else []
        )
        reading["off_rubric"]["red_flags"] = [_text(v, 300) for v in flags][:MAX_OFF_RUBRIC_ITEMS]
        reading["off_rubric"]["hidden_strengths"] = [_text(v, 300) for v in strengths][
            :MAX_OFF_RUBRIC_ITEMS
        ]

    risks = raw.get("semantic_risks") if isinstance(raw.get("semantic_risks"), list) else []
    reading["semantic_risks"] = [_text(v, 300) for v in risks][:MAX_SEMANTIC_RISKS]

    return reading


def evidence_reading_risk_flags(reading: dict) -> list[str]:
    """String risk flags for ``decision_state.risk_flags``.

    Derives conservative, deterministic flags from the reading: off-rubric red
    flags, cross-answer risks, and a count of answers whose claims are not
    backed by verifiable specifics. These only ever add risk — they can never
    boost a verdict or confidence.
    """
    reading = reading or {}
    flags: list[str] = []

    for flag in reading.get("off_rubric", {}).get("red_flags", []):
        flags.append(f"off-rubric flag: {flag}")

    for risk in reading.get("semantic_risks", []):
        flags.append(f"cross-answer risk: {risk}")

    per = reading.get("per_answer", {}) or {}
    unverified = sum(1 for e in per.values() if not e.get("verifiable"))
    if unverified >= 3:
        flags.append(f"{unverified} answer(s) with claims not backed by specifics")

    return flags


def evidence_reading_checks(reading: dict) -> list[dict]:
    """Semantic review checks in the ``{issue, severity, detail}`` shape used by
    ``review_decision``. Severity is capped at ``medium`` so these flag for
    review and trim confidence but never demote a decisive verdict on their own.
    """
    reading = reading or {}
    checks: list[dict] = []

    red_flags = reading.get("off_rubric", {}).get("red_flags", []) or []
    if red_flags:
        checks.append({
            "issue": "off_rubric_flag",
            "severity": MAX_SEMANTIC_SEVERITY,
            "detail": f"{len(red_flags)} off-rubric flag(s): {'; '.join(red_flags[:2])}",
        })

    risks = reading.get("semantic_risks", []) or []
    if risks:
        checks.append({
            "issue": "cross_answer_risk",
            "severity": MAX_SEMANTIC_SEVERITY,
            "detail": f"{len(risks)} cross-answer risk(s): {'; '.join(risks[:2])}",
        })

    per = reading.get("per_answer", {}) or {}
    unverified = sum(1 for e in per.values() if not e.get("verifiable"))
    if unverified >= 3:
        checks.append({
            "issue": "unverifiable_claims",
            "severity": MAX_SEMANTIC_SEVERITY,
            "detail": f"{unverified} answer(s) claimed skills without verifiable specifics.",
        })

    return checks


def transcript_payload(evidence_store: list[dict]) -> list[dict]:
    """Deterministic, size-capped transcript slice for the LLM prompt."""
    payload = []
    for ev in (evidence_store or [])[:MAX_TRANSCRIPT_ITEMS]:
        payload.append({
            "evidence_id": ev.get("id", ""),
            "question_number": ev.get("question_number"),
            "competency": ev.get("competency", ""),
            "dimension": ev.get("dimension", ""),
            "score": ev.get("score"),
            "evidence_text": _text(ev.get("evidence_text"), MAX_ANSWER_CHARS),
        })
    return payload
