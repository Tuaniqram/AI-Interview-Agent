"""Evidence Reading V5 — semantic read of the actual answers.

Turns the LLM's transcript reading into a structured, deterministic
``evidence_reading`` dict that downstream layers consume as *signals*. The LLM
never scores or decides: it classifies each answer's claims and surfaces
off-rubric observations, and the deterministic engine decides what to do with
them.

Plan step 7: the read is SECONDARY. Per-answer verifiability comes from the evaluator (step 4) and
contradictions from the claim ledger (step 5); the read keeps downgrade-only claim classification,
off-rubric flags and a cross-check for contradictions the ledger missed. It reads one entry per
answered question (``transcript_by_question``) and never demotes a verdict.

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
# The whole transcript the reader sees; long answers are trimmed in the middle so no question is dropped.
MAX_TRANSCRIPT_CHARS = 24_000
_TRIM_MARK = " … "

_ACCEPTED_KEYS = (
    "claim_classification",
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

    Only the fields the prompt declares are accepted. Plan step 7: entries are per QUESTION
    (``question_number``) and fan out to every evidence record of that question, so ``per_answer`` stays
    keyed by evidence id for its consumers; ``per_question`` keeps the read by question. An entry for a
    question that has no evidence (the reader cited "Q16" in a 14-question run) or an unknown
    ``evidence_id`` is dropped, so a hallucinated reference can never enter the brain. Fully deterministic.
    """
    records = {str(ev.get("id", "")): ev for ev in (evidence_store or [])}
    by_question: dict[int, list[str]] = {}
    for ev in evidence_store or []:
        try:
            qn = int(ev.get("question_number") or 0)
        except (TypeError, ValueError):
            continue
        if qn > 0 and ev.get("id"):
            by_question.setdefault(qn, []).append(str(ev["id"]))
    raw = llm_output if isinstance(llm_output, dict) else {}

    reading: dict[str, Any] = {
        "per_answer": {},
        "per_question": {},
        "off_rubric": {"red_flags": [], "hidden_strengths": []},
        "semantic_risks": [],
    }

    per_answer = raw.get("per_answer") or []
    if isinstance(per_answer, list):
        for item in per_answer[:MAX_PER_ANSWER]:
            if not isinstance(item, dict):
                continue
            entry = {
                "claim_classification": _clean(
                    item.get("claim_classification"), CLAIM_NAMES, "mentioned"
                ),
                "specificity": _clean(item.get("specificity"), SPECIFICITY_LEVELS, "low"),
                "ownership": _clean(item.get("ownership"), OWNERSHIP_LEVELS, "vague"),
                "supporting_metric": _text(item.get("supporting_metric")),
                "quote": _text(item.get("quote"), 300),
            }
            qn = item.get("question_number")
            try:
                qn = int(qn) if qn is not None else None
            except (TypeError, ValueError):
                qn = None
            if qn is not None:
                ids = by_question.get(qn)
                if not ids:
                    continue  # invented question number
                reading["per_question"][qn] = {**entry, "question_number": qn}
                for ev_id in ids:
                    reading["per_answer"][ev_id] = {**entry, "evidence_id": ev_id, "question_number": qn}
                continue
            ev_id = str(item.get("evidence_id", ""))  # legacy per-evidence shape
            if not ev_id or ev_id not in records:
                continue
            reading["per_answer"][ev_id] = {**entry, "evidence_id": ev_id}

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

    # (Unverifiable answers are now counted from the evaluator's answer_signals, plan step 7.)
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
            "count": len(red_flags),
            "detail": f"{len(red_flags)} off-rubric flag(s): {'; '.join(red_flags[:2])}",
        })

    risks = reading.get("semantic_risks", []) or []
    if risks:
        # Plan step 7: flags for human review only, never demotes. Changed figures are demoted by the claim
        # ledger's deterministic caps (7 / 7b); this is the cross-check for what the ledger missed.
        checks.append({
            "issue": "cross_answer_risk",
            "severity": MAX_SEMANTIC_SEVERITY,
            "count": len(risks),
            "detail": f"{len(risks)} cross-answer risk(s): {'; '.join(risks[:2])}",
        })

    # (The unverifiable-claims check moved to the deterministic unsubstantiated share, plan steps 4 and 7.)
    return checks


def _trim_middle(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    keep = max(0, limit - len(_TRIM_MARK))
    head = keep - keep // 2
    return text[:head].rstrip() + _TRIM_MARK + text[len(text) - keep // 2:].lstrip()


def _answers_by_question(state: dict) -> dict[int, str]:
    """The candidate's raw reply to each asked question, from the conversation history.

    A question's reply is every user message after that question was asked and before the next asked
    question (a clarification exchange stays inside its question)."""
    questions = [
        str(q.get("text") or "").strip()
        for q in state.get("questions_asked") or []
        if isinstance(q, dict)
    ]
    answers: dict[int, list[str]] = {}
    current = 0
    next_index = 0
    for msg in state.get("conversation_history") or []:
        if not isinstance(msg, dict):
            continue
        content = str(msg.get("content") or "").strip()
        if msg.get("role") == "assistant":
            # Advance only on the NEXT asked question (clarification replies are not questions).
            for i in range(next_index, len(questions)):
                if questions[i] and content == questions[i]:
                    current, next_index = i + 1, i + 1
                    break
        elif msg.get("role") == "user" and current and content:
            answers.setdefault(current, []).append(content)
    return {q: "\n".join(parts) for q, parts in answers.items()}


def transcript_by_question(state: dict, max_chars: int = MAX_TRANSCRIPT_CHARS) -> list[dict]:
    """One item per answered question: ``{question_number, question, answer, evidence_ids}``.

    Plan step 7: the reader used to get the first 20 evidence records (quotes, not answers) and missed the
    end of every long interview. Now every answered question is included; when the total is over
    ``max_chars`` the longest answers are trimmed in the middle (water-filling), never dropped.
    """
    evidence = state.get("evidence_store") or []
    ev_ids: dict[int, list[str]] = {}
    quotes: dict[int, str] = {}
    for ev in evidence:
        try:
            qn = int(ev.get("question_number") or 0)
        except (TypeError, ValueError):
            continue
        if qn <= 0:
            continue
        if ev.get("id"):
            ev_ids.setdefault(qn, []).append(str(ev["id"]))
        quotes.setdefault(qn, str(ev.get("answer_evidence_text") or ev.get("evidence_text") or ""))
    asked = [q for q in state.get("questions_asked") or [] if isinstance(q, dict)]
    replies = _answers_by_question(state)

    items = []
    for qn in sorted(set(ev_ids) | set(replies)):
        question = str(asked[qn - 1].get("text") or "") if 0 < qn <= len(asked) else ""
        items.append({
            "question_number": qn,
            "question": _trim_middle(question, 600),
            "answer": replies.get(qn) or quotes.get(qn, ""),
            "evidence_ids": ev_ids.get(qn, []),
        })

    # Water-filling: every answer gets an equal share of what is left; short ones keep their full text.
    fixed = sum(len(i["question"]) + 80 for i in items)
    budget = max(0, max_chars - fixed)
    pending = sorted(items, key=lambda i: len(i["answer"]))
    remaining = len(pending)
    for item in pending:
        share = budget // remaining if remaining else 0
        if len(item["answer"]) > share:
            item["answer"] = _trim_middle(item["answer"], max(200, share))
        budget -= len(item["answer"])
        remaining -= 1
    return items
