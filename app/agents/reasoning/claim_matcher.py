"""Deterministic claim matching: find measurable figures in answers and decide which ones are about the same metric.

An experiment, not wired into the interview. Today the evaluator (an LLM) lists each answer's claims and names their metric
(``metric_key``), and the claim ledger compares figures that share a name. This module does the finding and naming in code:

1. ``extract_figures``  every number with a unit in an answer ("87%", "4 hours to 35 minutes", "2 million requests per
                        second", "under 50 ms"), parsed with the ledger's own ``parse_value``, plus the sentence it sits in.
2. ``assign_metric_keys`` groups figures from different answers when their units are comparable and the sentences around
                        them describe the same thing: cosine similarity of the sentences (numbers masked out) above a
                        threshold, and at least one shared metric word ("settlement", "latency", "uptime"), so "latency
                        dropped 40%" and "cost dropped 40%" stay apart.
3. ``detect_code_conflicts`` runs the ledger's ``detect_conflicts`` on those groups, so changed figures are judged by exactly
                        the same rules as the LLM path.

Code cannot see an explicit correction ("actually it was 91%") or an admission that a figure was inflated; those stay
with the evaluator. ``tools/claim_replay`` compares the two methods on saved simulated interviews.
"""
from __future__ import annotations

import math
import re
from typing import Callable, Iterable, Optional

from app.agents.reasoning.claim_ledger import _LOWER_RE, _UPPER_RE, ParsedValue, detect_conflicts, parse_value

Similarity = Callable[[str, str], float]

DEFAULT_THRESHOLD = 0.55
# Above this similarity two contexts match even without a shared metric word.
STRONG_THRESHOLD = 0.80

_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_MAG = r"(?:thousand|millions?|billions?|bn|k|m|b)(?![a-z])"
_UNIT = (
    r"%|percent\b|pct\b|x\b|×|times\b|fold\b"
    r"|ms\b|msec\b|milliseconds?\b|s\b|secs?\b|seconds?\b|mins?\b|minutes?\b|h\b|hrs?\b|hours?\b|days?\b"
    r"|kb\b|mb\b|gb\b|tb\b"
    r"|rps\b|qps\b|tps\b|rpm\b|req/s\b|requests?/s(?:ec)?\b"
    # A counted noun, after at most one describing word: "4 million transactions", "4 million daily transactions".
    r"|(?:(?:daily|monthly|weekly|hourly|active|concurrent|unique|total|peak|new|paying|registered)\s+)?[a-z][a-z-]{2,}"
)
_DESCRIBING_WORDS = {"daily", "monthly", "weekly", "hourly", "active", "concurrent", "unique", "total", "peak", "new",
                     "paying", "registered"}
_BOUND = r"(?:sub[-‑\s]?|<=?|≤|under\s|below\s|less than\s|up to\s|at most\s|within\s|no more than\s|>=?|≥|over\s|above\s|more than\s|at least\s|upwards of\s)"
# A number glued to letters is a name, not a figure: "p99", "EC2", "S3", "v2".
_POINT = rf"(?:{_BOUND})?\$?(?<![A-Za-z0-9.])(?:{_NUM})\s*(?:{_MAG})?\s*(?:{_UNIT})?"
# "between 3 and 5 nodes", "from 4 hours to 35 minutes", "120 ms → 12 ms", or one figure. "and" joins a range only after
# "between": "latency 87% and load 40%" are two figures.
_FIGURE_RE = re.compile(
    rf"between\s+{_POINT}\s*and\s*{_POINT}"
    rf"|(?:from\s+)?{_POINT}(?:\s*(?:to|→|->|–|—|-)\s*{_POINT})?",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"^(?:19[7-9]\d|20[0-3]\d)$")
_SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+|\n+")

# Words after a number that are not a unit or a counted thing ("3 of them", "2 and 4", "step 1 is").
_NOT_A_UNIT = {
    "and", "or", "of", "to", "the", "a", "an", "in", "on", "for", "with", "at", "by", "is", "was", "were", "are",
    "then", "than", "from", "into", "per", "plus", "but", "so", "as", "it", "we", "i", "my", "our", "that", "this",
    "which", "when", "after", "before", "out", "more", "less", "times",
}
_STOPWORDS = _NOT_A_UNIT | {
    "be", "been", "being", "have", "has", "had", "do", "did", "does", "not", "no", "about", "around", "roughly",
    "approximately", "nearly", "almost", "over", "under", "just", "only", "also", "very", "really", "there", "their",
    "they", "them", "you", "your", "us", "me", "what", "how", "why", "where", "who", "all", "any", "each", "some",
    "num", "can", "could", "would", "will", "should", "while", "during", "between", "both", "one", "two", "three",
    "like", "such", "these", "those", "its", "his", "her", "up", "down", "back", "again", "once",
}
# Verbs and fillers that describe a change, not what changed: sharing them does not make two figures the same metric.
_GENERIC = {
    "reduce", "reduced", "reduction", "reducing", "drop", "dropped", "drops", "cut", "cuts", "improve", "improved",
    "improvement", "increase", "increased", "decrease", "decreased", "lower", "lowered", "raise", "raised", "boost",
    "boosted", "achieve", "achieved", "get", "got", "went", "brought", "bring", "go", "make", "made", "keep", "kept",
    "saw", "see", "seen", "result", "resulted", "gain", "gained", "fell", "fall", "rose", "rise", "grew", "grow",
    "slashed", "average", "total", "overall", "roughly", "number", "figure", "metric", "value", "rate", "level",
    "time", "times", "percent", "percentage", "faster", "slower", "higher", "smaller", "bigger", "better", "worse",
}


def _sentences(text: str) -> list[tuple[int, int, str]]:
    out, pos = [], 0
    for part in _SENTENCE_RE.split(text or ""):
        start = (text or "").find(part, pos)
        if start < 0:
            start = pos
        out.append((start, start + len(part), part))
        pos = start + len(part)
    return out


def _is_figure(span: str, parsed: ParsedValue) -> bool:
    if parsed.number is None:
        return False
    if parsed.unit in ("%", "x", "s", "mb", "rps", "rpm"):
        return True
    unit = parsed.unit
    if not unit:
        return False  # a bare number ("Python 3", "step 2") is not a claim
    if unit in _NOT_A_UNIT:
        return False
    bare = re.sub(r"[^\d.]", "", span.split()[0]) if span.split() else ""
    if _YEAR_RE.match(bare):
        return False  # "2019 we migrated"
    return True


def mask_numbers(text: str) -> str:
    """The sentence with every figure replaced by NUM: similarity should be about the metric, not the value."""
    return re.sub(rf"(?:{_NUM})\s*(?:{_MAG})?", " NUM ", text or "", flags=re.IGNORECASE)


def _stem(word: str) -> str:
    for suffix in ("ations", "ation", "ings", "ing", "ies", "es", "ed", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def metric_terms(text: str) -> set[str]:
    """Content words that can name a metric (numbers, stop words and change verbs removed), lightly stemmed."""
    words = re.findall(r"[a-z][a-z-]+", mask_numbers(text).lower())
    return {_stem(w) for w in words if len(w) >= 3 and w not in _STOPWORDS and w not in _GENERIC}


def extract_figures(answer: str, question_number: int) -> list[dict]:
    """Every measurable figure in one answer, with the ledger's parsed value and its sentence."""
    figures: list[dict] = []
    # Thin and no-break spaces are ordinary spaces, and a space between digit groups is a thousands separator:
    # "1 000 tasks", "14 400 s" (otherwise "000 tasks" and "400 s" would be read as figures).
    answer = re.sub(r"[    ]", " ", answer or "")
    answer = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", answer)
    for s_start, s_end, sentence in _sentences(answer):
        for m in _FIGURE_RE.finditer(sentence):
            span = m.group(0).strip()
            if not re.search(r"\d", span):
                continue
            # A counted noun that is really a stop word ("3 of them"): trim it so parse_value sees no unit.
            last = span.split()[-1].lower() if span.split() else ""
            if last in _NOT_A_UNIT:
                span = span[: span.lower().rfind(last)].strip()
            parsed = parse_value(span)
            if parsed.number is not None and parsed.unit in _DESCRIBING_WORDS:
                parsed = parsed._replace(unit=span.split()[-1].lower())  # "4 million daily transactions"
            if parsed.number is not None and not parsed.unit and "$" in span:
                parsed = parsed._replace(unit="usd")  # "$20k"
            if parsed.bound is None:
                # A bound word just before the figure ("stayed under 50 ms" where the match starts at the number).
                prefix = sentence[max(0, m.start() - 16): m.start()]
                bound = "upper" if _UPPER_RE.search(prefix) else "lower" if _LOWER_RE.search(prefix) else None
                parsed = parsed._replace(bound=bound)
            if not _is_figure(span, parsed):
                continue
            figures.append({
                "question_number": int(question_number),
                "value_text": span,
                "number": parsed.number,
                "unit": parsed.unit,
                "range": parsed.is_range,
                "bound": parsed.bound,
                "context": sentence.strip(),
                "window": figure_window(sentence, m.start(), m.end()),
            })
    return figures


_CLAUSE_BREAK_RE = re.compile(r"[,;:()\[\]]|\s[—–-]\s|—|–")
WINDOW_BEFORE = 8
WINDOW_AFTER = 6


def figure_window(sentence: str, start: int, end: int) -> str:
    """The words that say what a figure measures: its own clause, at most WINDOW_BEFORE words before and WINDOW_AFTER after.
    A long sentence often carries several metrics ("a 0.5 s SLA ..., rolls back in under 300 ms, cutting errors to 0.01%"),
    so the whole sentence would make unrelated figures look alike."""
    breaks = [0] + [b.end() for b in _CLAUSE_BREAK_RE.finditer(sentence)] + [len(sentence)]
    left = max(b for b in breaks if b <= start)
    right = min((b.start() for b in _CLAUSE_BREAK_RE.finditer(sentence, end)), default=len(sentence))
    before = sentence[left:start].split()
    if len(before) < 2 and left > 0:
        # "Cache hits: 98%" - the clause before says what the figure is.
        prev_left = max((b for b in breaks if b < left - 1), default=0)
        before = sentence[prev_left:start].split()
    after = sentence[end:right].split()
    return " ".join(before[-WINDOW_BEFORE:] + [sentence[start:end].strip()] + after[:WINDOW_AFTER])


def _comparable_units(a: dict, b: dict) -> bool:
    return bool(a.get("unit")) and a.get("unit") == b.get("unit")


def lexical_similarity(a: str, b: str) -> float:
    """Jaccard overlap of metric words: the fallback when no embedding model is available."""
    ta, tb = metric_terms(a), metric_terms(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def cosine(u: Iterable[float], v: Iterable[float]) -> float:
    u, v = list(u), list(v)
    nu, nv = math.sqrt(sum(x * x for x in u)), math.sqrt(sum(y * y for y in v))
    if not nu or not nv:
        return 0.0
    return sum(x * y for x, y in zip(u, v)) / (nu * nv)


def same_metric(
    a: dict,
    b: dict,
    similarity: Similarity,
    threshold: float = DEFAULT_THRESHOLD,
    strong_threshold: float = STRONG_THRESHOLD,
) -> tuple[bool, float, set[str]]:
    """Are two figures about the same metric? Returns (decision, similarity, shared metric words)."""
    if not _comparable_units(a, b):
        return False, 0.0, set()
    wa, wb = a.get("window") or a["context"], b.get("window") or b["context"]
    score = float(similarity(mask_numbers(wa), mask_numbers(wb)))
    shared = metric_terms(wa) & metric_terms(wb)
    decision = score >= strong_threshold or (score >= threshold and bool(shared))
    return decision, score, shared


def assign_metric_keys(
    figures: list[dict],
    similarity: Similarity,
    threshold: float = DEFAULT_THRESHOLD,
    strong_threshold: float = STRONG_THRESHOLD,
) -> list[dict]:
    """Give every figure a ``metric_key``: the key of the most similar figure from an EARLIER answer when it is the same
    metric, else a new key. Figures in one answer never merge with each other (one answer states a figure once)."""
    keyed: list[dict] = []
    counter = 0
    for fig in sorted(figures, key=lambda f: f["question_number"]):
        best: Optional[tuple[float, dict, set]] = None
        for other in keyed:
            if other["question_number"] >= fig["question_number"]:
                continue
            ok, score, shared = same_metric(fig, other, similarity, threshold, strong_threshold)
            if ok and (best is None or score > best[0]):
                best = (score, other, shared)
        if best:
            key = best[1]["metric_key"]
            match = {"question_number": best[1]["question_number"], "similarity": round(best[0], 3),
                     "shared_terms": sorted(best[2])}
        else:
            counter += 1
            key = f"fig_{counter}"
            match = None
        keyed.append({**fig, "metric_key": key, "matched": match})
    return keyed


def detect_code_conflicts(keyed: list[dict]) -> list[dict]:
    """Changed figures among code-keyed claims, judged by the claim ledger's own rules."""
    conflicts: list[dict] = []
    for qn in sorted({f["question_number"] for f in keyed}):
        new = [{**f, "competency": "", "evidence_ids": []} for f in keyed if f["question_number"] == qn]
        earlier = [{**f, "competency": "", "evidence_ids": []} for f in keyed if f["question_number"] < qn]
        found = detect_conflicts(earlier + new, new, question_number=qn, existing=conflicts)
        conflicts.extend(found)
    return conflicts
