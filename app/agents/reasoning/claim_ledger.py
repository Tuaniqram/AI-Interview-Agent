"""Claim ledger (plan step 5, design D4) — contradictions in the candidate's own words.

Pure and deterministic. The evaluator (step 4) lists every measurable claim of an answer with a
``metric_key``; this module keeps those claims across the interview and detects when the candidate
changes a figure ("87%" at Q2, "92%" at Q5), explicitly corrects one, or admits a figure was inflated.
Conflicts are recorded in ``claim_conflicts`` and mirrored into ``contradictions`` (type
``claim_conflict``) so every existing consumer — sufficiency, director, difficulty, decision — sees them.

Statuses: ``open`` (detected) → ``asked`` (a reconcile question was put, step 6) → ``explained`` /
``unexplained``. Only ``explained`` conflicts stop counting against the candidate.
"""
from __future__ import annotations

import re
from typing import NamedTuple
from uuid import uuid4

UNRESOLVED_STATUSES = ("open", "asked", "unexplained")
# A changed figure is a conflict when it moved by more than this share of the larger value ...
MIN_RELATIVE_CHANGE = 0.10
# ... or, for percentages, by more than this many points (0.02% vs 0.04% is noise; 87% vs 92% is not,
# although it is only 5% relative — the plan's 10%-relative rule alone would miss the bluffer's 93% vs 85%).
MIN_PERCENT_POINTS = 1.0

__all__ = [
    "ParsedValue",
    "UNRESOLVED_STATUSES",
    "parse_value",
    "fold_claims",
    "detect_conflicts",
    "known_claims_brief",
    "next_conflict_to_reconcile",
    "settle_after_reconcile",
    "unresolved_conflicts",
    "mark_asked",
    "apply_claim_ledger",
]


class ParsedValue(NamedTuple):
    number: float | None
    unit: str
    is_range: bool
    bound: str | None = None  # "upper" ("sub-50 ms", "<12 ms", "under 2 s") / "lower" ("over 1M", "at least 99%")


_MAGNITUDES = {
    "k": 1e3, "thousand": 1e3,
    "m": 1e6, "mm": 1e6, "million": 1e6, "millions": 1e6,
    "b": 1e9, "bn": 1e9, "billion": 1e9, "billions": 1e9,
}
# Time units normalized to seconds so "4 hours" and "30 minutes" compare.
_TIME_UNITS = {
    "ms": 1e-3, "msec": 1e-3, "millisecond": 1e-3, "milliseconds": 1e-3,
    "s": 1.0, "sec": 1.0, "secs": 1.0, "second": 1.0, "seconds": 1.0,
    "min": 60.0, "mins": 60.0, "minute": 60.0, "minutes": 60.0,
    "h": 3600.0, "hr": 3600.0, "hrs": 3600.0, "hour": 3600.0, "hours": 3600.0,
    "day": 86400.0, "days": 86400.0,
}
_SIZE_UNITS = {"kb": 1e-3, "mb": 1.0, "gb": 1e3, "tb": 1e6}
_RATE_ALIASES = {"rps": "rps", "qps": "rps", "tps": "rps", "req/s": "rps", "requests/s": "rps",
                 "requests/sec": "rps", "rpm": "rpm"}
# Bound words just before the number. "sub-50 ms" and "45 ms" agree; so do "<12 ms" and "<10 ms".
_UPPER_RE = re.compile(r"(sub[-‑\s]?|<=?|≤|\bunder|\bbelow|\bless than|\bup to|\bat most|\bwithin|\bno more than)\s*$",
                       re.IGNORECASE)
_LOWER_RE = re.compile(r"(>=?|≥|\bover|\babove|\bmore than|\bat least|\bupwards of)\s*$", re.IGNORECASE)
_RANGE_RE = re.compile(r"\b(from|between)\b|\bto\b|→|->|–|—|(?<=\d)\s*-\s*(?=\d)", re.IGNORECASE)
_NUMBER_RE = re.compile(
    r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*"
    r"(?:(?P<mag>thousand|millions?|billions?|bn|mm|k|m|b)(?![a-z]))?\s*"
    r"(?P<unit>%|x\b|×|req/s|requests/sec|requests/s|[a-zA-Z]+)?",
    re.IGNORECASE,
)


# "no …" is deliberately absent: "no number here" is not a zero.
_ZERO_WORDS_RE = re.compile(r"^\s*(zero|none|nil|never)\b", re.IGNORECASE)


def parse_value(text: str) -> ParsedValue:
    """Number and unit of a claim value. Ranges ("from 120 ms to 12 ms") keep the last number and are
    marked ``is_range`` so they are never compared. "zero" / "none" / "no …" read as 0."""
    text = str(text or "").strip()
    matches = list(_NUMBER_RE.finditer(text))
    if not matches:
        if _ZERO_WORDS_RE.search(text):
            return ParsedValue(0.0, "", False)
        return ParsedValue(None, "", False)
    is_range = len(matches) >= 2 and bool(_RANGE_RE.search(text))
    m = matches[-1] if is_range else matches[0]
    prefix = text[max(0, m.start() - 16):m.start()]
    bound = "upper" if _UPPER_RE.search(prefix) else "lower" if _LOWER_RE.search(prefix) else None
    # "no spikes above 5 ms" / "never more than 2%": a negated lower-bound word is an upper bound.
    if bound == "lower" and re.search(r"\b(no|never|not)\b", text[max(0, m.start() - 40):m.start()], re.IGNORECASE):
        bound = "upper"
    if bound is None and text[m.end():m.end() + 1] == "+":
        bound = "lower"  # "10k+ users"
    number = float(m.group("num").replace(",", ""))
    mag = (m.group("mag") or "").lower()
    unit = (m.group("unit") or "").strip()
    unit_l = unit.lower()

    # "2.1 m rps" vs "2.1 ms": a bare "m" is a magnitude only when another unit follows or none at all.
    if mag in ("m", "b") and unit_l in _TIME_UNITS:
        mag = ""
    number *= _MAGNITUDES.get(mag, 1.0)

    if unit == "%" or unit_l in ("percent", "pct"):
        return ParsedValue(number, "%", is_range, bound)
    if unit_l in ("x", "×", "times", "fold"):
        return ParsedValue(number, "x", is_range, bound)
    if unit_l in _TIME_UNITS:
        return ParsedValue(round(number * _TIME_UNITS[unit_l], 9), "s", is_range, bound)
    if unit_l in _SIZE_UNITS:
        return ParsedValue(number * _SIZE_UNITS[unit_l], "mb", is_range, bound)
    if unit_l in _RATE_ALIASES:
        return ParsedValue(number, _RATE_ALIASES[unit_l], is_range, bound)
    return ParsedValue(number, unit_l, is_range, bound)


def fold_claims(
    ledger: list,
    claims: list,
    question_number: int,
    competency: str | None = None,
    evidence_ids: list | None = None,
) -> tuple[list, list]:
    """Add this answer's claims to the ledger. Returns ``(ledger, new_entries)``; a re-run for the same
    question replaces that question's entries instead of duplicating them."""
    kept = [e for e in (ledger or []) if int(e.get("question_number", -1)) != int(question_number)]
    new_entries = []
    for claim in claims or []:
        key = str((claim or {}).get("metric_key") or "").strip().lower()
        if not key:
            continue
        value_text = str(claim.get("value") or claim.get("quote") or "").strip()
        parsed = parse_value(value_text) if value_text else ParsedValue(None, "", False)
        if parsed.number is None and claim.get("quote"):
            parsed = parse_value(str(claim["quote"]))
        new_entries.append({
            "id": str(uuid4()),
            "metric_key": key,
            "value_text": value_text,
            "number": parsed.number,
            "unit": parsed.unit,
            "range": parsed.is_range,
            "bound": parsed.bound,
            "question_number": int(question_number),
            "competency": competency or "",
            "quote": str(claim.get("quote") or "").strip(),
            "evidence_ids": list(evidence_ids or []),
        })
    return kept + new_entries, new_entries


def _comparable(a: dict, b: dict) -> bool:
    if a.get("number") is None or b.get("number") is None or a.get("range") or b.get("range"):
        return False
    if a.get("unit") == b.get("unit"):
        return True
    # A bare zero ("0", "zero", "none") compares with any unit: "zero downtime" vs "2 minutes" is a changed story.
    return any(float(x["number"]) == 0 and not x.get("unit") for x in (a, b))


def _differs(x: float, y: float, unit: str) -> bool:
    """Percentages move in points (87% -> 92% is a changed story, 0.04% -> 0.02% is noise); every other
    unit by a relative share of the larger value (350 ms -> 340 ms is rounding)."""
    if unit == "%":
        return abs(x - y) > MIN_PERCENT_POINTS
    larger = max(abs(x), abs(y))
    return larger > 0 and abs(x - y) / larger > MIN_RELATIVE_CHANGE


def _changed(a: dict, b: dict) -> bool:
    """Do two comparable claims contradict each other? A bound only conflicts with a value that breaks it
    ("sub-50 ms" then "45 ms" agree; "under 50 ms" then "80 ms" do not); two bounds in the same direction
    never conflict ("<12 ms" then "<10 ms")."""
    x, y = float(a["number"]), float(b["number"])
    unit = a.get("unit") or b.get("unit") or ""
    ba, bb = a.get("bound"), b.get("bound")
    if not ba and not bb:
        # Absolute claims (step 10 gate): "0" next to a non-zero figure, or 100% next to anything less, is a
        # different story however close the numbers are ("100% availability" vs "99.99%").
        if (x == 0) != (y == 0):
            return True
        if unit == "%" and (x == 100) != (y == 100):
            return True
        return _differs(x, y, unit)
    if ba and bb:
        if ba == bb:
            return False
        upper, lower = (x, y) if ba == "upper" else (y, x)
        return lower > upper and _differs(lower, upper, unit)
    bound_value, value, kind = (x, y, ba) if ba else (y, x, bb)
    broken = value > bound_value if kind == "upper" else value < bound_value
    return broken and _differs(value, bound_value, unit)


_KIND_RANK = {"changed_value": 0, "explicit_correction": 1, "inflation_admitted": 2}
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


def _conflict(kind, severity, metric_key, first, second, competency, statement, evidence_ids=None) -> dict:
    return {
        "id": str(uuid4()),
        "type": "claim_conflict",
        "metric_key": metric_key,
        "first": first,
        "second": second,
        "kind": kind,
        "severity": severity,
        "status": "open",
        "asked_in_question": None,
        "statement": statement,
        "competency": competency or "",
        "evidence_ids": list(evidence_ids or []),
    }


def _ref(entry: dict) -> dict:
    return {"question_number": entry.get("question_number"), "value_text": entry.get("value_text")}


def detect_conflicts(
    ledger: list,
    new_entries: list,
    corrections: list | None = None,
    inflation_admitted: bool = False,
    question_number: int = 0,
    existing: list | None = None,
) -> list:
    """Conflicts created by this answer (not yet in ``existing``)."""
    earlier = [e for e in ledger or [] if int(e.get("question_number", 0)) < int(question_number)]
    # One conflict per (metric, answer): the evaluator often reports the same changed figure both as a new
    # value and as a correction (step 5 gate: "98% -> 54%" counted twice). The duplicate is merged, keeping
    # the stronger kind and severity.
    seen = {(c.get("metric_key"), (c.get("second") or {}).get("question_number")) for c in existing or []}
    found: list = []
    by_sig: dict = {}

    def add(conflict: dict) -> None:
        sig = (conflict["metric_key"], conflict["second"].get("question_number"))
        if sig in by_sig:
            kept = by_sig[sig]
            if _KIND_RANK[conflict["kind"]] > _KIND_RANK[kept["kind"]]:
                kept["kind"] = conflict["kind"]
                kept["statement"] = conflict["statement"]
            if _SEVERITY_RANK[conflict["severity"]] > _SEVERITY_RANK[kept["severity"]]:
                kept["severity"] = conflict["severity"]
            return
        if sig not in seen:
            seen.add(sig)
            by_sig[sig] = conflict
            found.append(conflict)

    for entry in new_entries or []:
        prior = [e for e in earlier if e.get("metric_key") == entry["metric_key"] and _comparable(e, entry)]
        if not prior:
            continue
        last = max(prior, key=lambda e: int(e.get("question_number", 0)))
        if _changed(last, entry):
            add(_conflict(
                "changed_value", "medium", entry["metric_key"], _ref(last), _ref(entry), entry.get("competency"),
                f"{entry['metric_key']}: {last.get('value_text')} (Q{last.get('question_number')}) vs "
                f"{entry.get('value_text')} (Q{entry.get('question_number')})",
                (last.get("evidence_ids") or []) + (entry.get("evidence_ids") or []),
            ))

    for corr in corrections or []:
        key = str((corr or {}).get("metric_key") or "").strip().lower()
        prior = [e for e in earlier if e.get("metric_key") == key]
        if not key or not prior:
            continue
        last = max(prior, key=lambda e: int(e.get("question_number", 0)))
        # A correction counts only when both figures are numbers in one unit that really differ: the
        # evaluator also reported non-corrections ("zero evictions" -> "hybrid LRU-LFU eviction").
        before = parse_value(str(corr.get("from") or last.get("value_text") or ""))
        after = parse_value(str(corr.get("to") or ""))
        if (
            before.number is None or after.number is None or before.unit != after.unit
            or before.is_range or after.is_range
            or not _changed(dict(before._asdict(), unit=before.unit), dict(after._asdict(), unit=after.unit))
        ):
            continue
        second = {"question_number": int(question_number), "value_text": str(corr.get("to") or "")}
        add(_conflict(
            "explicit_correction", "medium", key, _ref(last), second, last.get("competency"),
            f"{key}: corrected from {corr.get('from') or last.get('value_text')} (Q{last.get('question_number')}) "
            f"to {corr.get('to')} (Q{question_number})",
            last.get("evidence_ids"),
        ))

    if inflation_admitted:
        keys = [e["metric_key"] for e in new_entries or []] or [
            str(c.get("metric_key") or "").strip().lower() for c in corrections or [] if c.get("metric_key")
        ]
        key = keys[0] if keys else "unspecified_figure"
        prior = [e for e in earlier if e.get("metric_key") == key]
        first = _ref(max(prior, key=lambda e: int(e.get("question_number", 0)))) if prior else {}
        add(_conflict(
            "inflation_admitted", "high", key, first, {"question_number": int(question_number), "value_text": ""},
            (prior[0].get("competency") if prior else ""),
            f"Q{question_number}: the candidate said a figure ({key}) was inflated or not real",
        ))
    return found


def unresolved_conflicts(conflicts: list | None) -> list:
    return [c for c in conflicts or [] if c.get("status", "open") in UNRESOLVED_STATUSES]


def _escalate(conflicts: list) -> list:
    """A second unresolved conflict on any metric raises every unresolved conflict to high."""
    open_ = unresolved_conflicts(conflicts)
    if len(open_) >= 2:
        for c in open_:
            c["severity"] = "high"
    return conflicts


def known_claims_brief(ledger: list | None, limit: int = 30) -> str:
    """``metric_key: value (Qn)`` for the evaluator prompt (latest value per key), or "None".

    30, not 12: a talkative candidate states 50+ figures, and with 12 the early keys fell off the list
    before the candidate repeated the figure, so the evaluator could not reuse them (step 5 gate)."""
    latest: dict[str, dict] = {}
    for e in ledger or []:
        key = e.get("metric_key")
        if key and (key not in latest or int(e.get("question_number", 0)) >= int(latest[key].get("question_number", 0))):
            latest[key] = e
    items = sorted(latest.values(), key=lambda e: -int(e.get("question_number", 0)))[:limit]
    return "; ".join(f"{e['metric_key']}: {e.get('value_text')} (Q{e.get('question_number')})" for e in items) or "None"


def next_conflict_to_reconcile(conflicts: list | None) -> dict | None:
    """The oldest ``open`` conflict between two figures (step 6 asks about it).

    An admitted inflation is not a pair of figures to reconcile — the candidate already said the number was not
    real — so it is never asked about and keeps its cap (step 6 gate: one was "explained" by a fluent story)."""
    open_ = [
        c for c in conflicts or []
        if c.get("status", "open") == "open" and c.get("kind") != "inflation_admitted"
    ]
    return min(open_, key=lambda c: int((c.get("second") or {}).get("question_number") or 0)) if open_ else None


def settle_after_reconcile(conflict: dict, answer_signal: dict | None, created_new_conflict: bool = False) -> dict:
    """After the reconcile question is answered: ``explained`` when that answer was substantiated — judged
    verifiable AND carrying no unsupported claims — and created no new conflict (severity drops to low and it
    never blocks a hire); else ``unexplained``. In the step 6 gate a fluent bluffer "explained" every conflict
    with a new, unbacked measurement story ("200,000 unit tests"); the unsupported claims are what give it away."""
    settled = dict(conflict)
    signal = answer_signal or {}
    substantiated = signal.get("verifiable") is True and not signal.get("unsupported_claims")
    if conflict.get("kind") != "inflation_admitted" and substantiated and not created_new_conflict:
        settled["status"] = "explained"
        settled["severity"] = "low"
    else:
        settled["status"] = "unexplained"
    return settled


def mark_asked(state: dict, conflict_id: str | None, question_number: int) -> dict:
    """Plan step 6: the conflict was put to the candidate in ``question_number`` (asked once, never again).
    Returns the updated ``claim_conflicts`` and ``contradictions`` for the caller to merge into its state."""
    conflicts = []
    for c in state.get("claim_conflicts") or []:
        c = dict(c)
        if conflict_id and c.get("id") == conflict_id and c.get("status", "open") == "open":
            c["status"] = "asked"
            c["asked_in_question"] = int(question_number)
        conflicts.append(c)
    others = [c for c in state.get("contradictions") or [] if c.get("type") != "claim_conflict"]
    return {"claim_conflicts": conflicts, "contradictions": others + [_mirror(c) for c in conflicts]}


def _mirror(conflict: dict) -> dict:
    return {
        "id": conflict["id"],
        "type": "claim_conflict",
        "competency": conflict.get("competency", ""),
        "statement": conflict.get("statement", ""),
        "severity": conflict.get("severity", "medium"),
        "status": conflict.get("status", "open"),
        "evidence_ids": list(conflict.get("evidence_ids") or []),
    }


def apply_claim_ledger(state: dict) -> dict:
    """Engine wiring: fold this answer's claims, detect conflicts, mirror them into ``contradictions``."""
    extras = state.get("unified_evaluation_extras") or {}
    question_number = int(state.get("question_number", 0) or 0)
    extracted = state.get("extracted_evidence") or []
    competency = (
        (extracted[0].get("competency") if extracted else None)
        or (state.get("question_objective") or {}).get("target_competency")
        or ""
    )
    ledger, new_entries = fold_claims(
        state.get("claim_ledger") or [], extras.get("claims") or [], question_number, competency,
        [e.get("id") for e in extracted if e.get("id")],
    )
    conflicts = [dict(c) for c in state.get("claim_conflicts") or []]
    # Plan step 6: was this answer the reply to a reconcile question?
    asked = next(
        (c for c in conflicts if c.get("status") == "asked" and int(c.get("asked_in_question") or -1) == question_number),
        None,
    )
    new_conflicts = detect_conflicts(
        ledger, new_entries, extras.get("corrects_earlier_claim") or [],
        bool(extras.get("inflation_admitted")), question_number, existing=conflicts,
    )
    if asked is not None:
        # The reply is ABOUT the two figures: restating them under the same key (e.g. "the 87% was p50, the 93%
        # p95") is the explanation, not a new conflict. Anything on another metric still counts.
        new_conflicts = [c for c in new_conflicts if c.get("metric_key") != asked.get("metric_key")]
        signal = next(
            (s for s in state.get("answer_signals") or [] if int(s.get("question_number", -1)) == question_number),
            None,
        )
        settled = settle_after_reconcile(asked, signal, created_new_conflict=bool(new_conflicts))
        conflicts = [settled if c.get("id") == asked.get("id") else c for c in conflicts]
    conflicts.extend(new_conflicts)
    conflicts = _escalate(conflicts)

    # Mirrors are rebuilt from the conflicts every turn, so an escalation or a settled status is reflected.
    others = [c for c in state.get("contradictions") or [] if c.get("type") != "claim_conflict"]
    return {
        **state,
        "claim_ledger": ledger,
        "claim_conflicts": conflicts,
        "contradictions": others + [_mirror(c) for c in conflicts],
    }
