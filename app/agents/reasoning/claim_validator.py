"""Claim validator (F5) — authenticity signals over the candidate's answers.

Deterministic and offline. Detects the patterns that make an answer read like
polished filler instead of lived experience:

    * repeated verbatim phrases across different answers (a candidate recycling
      one narrative for every question)
    * generic senior-speak ("seasoned", "holistic", "orchestrated") with no
      substance behind it
    * lack of quantification (no numbers, percentages, or units)

Produces ``claim_signals`` stored on the brain each turn and used by the
explainable scoring and decision layers to temper inflated scores.
"""
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

# Numbers with units / % / currency / magnitude markers — the fingerprint of a
# quantified claim ("cut latency 40%", "9x throughput", "10k users", "$2m ARR").
_QUANT_RE = re.compile(
    r"(?<!\w)\d+(?:\.\d+)?\s*(?:%|[x×]|ms|s\b|secs?|seconds|req/s|qps|rps|tps|"
    r"users|requests|concurrent|gb|tb|mb|hours|days|weeks|usd|\$|k|m|million|thousand|"
    r"users|downtime|uptime|latency|error rate|conversion|retention)\b"
)
# Word- and number-anchored quantification ("reduced by", "improved 3x").
_QUANT_VERB_RE = re.compile(
    r"\b(reduced?|reduction|improved?|increased?|decreased?|cut|saved|boosted|"
    r"optimized|dropped|lowered|halved|doubled|tripled|grew|scaled|achieved|"
    r"latency|throughput|uptime|error rate|conversion|retention)\b",
    re.IGNORECASE,
)

# Generic senior-speak that carries no evidence on its own.
_GENERIC_TERMS = [
    "seasoned",
    "orchestrat",
    "holistic",
    "synergy",
    "robust",
    "seamless",
    "passionate",
    "dedicated",
    "hardworking",
    "team player",
    "deep understanding",
    "strong communication",
    "proven track record",
    "results-driven",
    "detail-oriented",
    "self-starter",
    "outside the box",
    "think outside",
    "leverage",
    "synergize",
    "world-class",
    "best-in-class",
]

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "for", "with",
    "that", "this", "was", "were", "had", "have", "has", "it", "at", "as", "by",
    "i", "my", "me", "we", "our", "us", "you", "your", "be", "been", "being",
    "is", "are", "do", "did", "does", "so", "then", "than", "if", "about", "into",
}


def _sentences(answer: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer or "") if len(s.strip()) > 30]


def _ngrams(text: str, n: int) -> list[str]:
    words = [w for w in re.findall(r"[a-z']+", text.lower()) if w not in _STOPWORDS]
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def repeated_phrases(answers: list[str], min_occurrences: int = 2, max_phrases: int = 3) -> list[str]:
    """Verbatim 4-6 word phrases appearing across *different* answers."""
    if len(answers) < 2:
        return []
    counters: list[Counter] = []
    for answer in answers:
        counts = Counter()
        for n in (4, 5, 6):
            for gram in _ngrams(answer, n):
                counts[gram] = 1
        counters.append(counts)

    global_hits = Counter()
    for counts in counters:
        for gram in counts:
            global_hits[gram] += 1

    repeated = [
        gram for gram, hits in global_hits.items()
        if hits >= min_occurrences
        and len(gram.split()) >= 4
    ]
    # Keep only the longest repeated phrase per answer cluster (drop sub-phrases).
    repeated.sort(key=lambda g: -len(g.split()))
    filtered: list[str] = []
    for gram in repeated:
        if any(gram in other for other in filtered):
            continue
        filtered.append(gram)
        if len(filtered) >= max_phrases:
            break
    return filtered


def generic_term_hits(answers: list[str]) -> list[str]:
    text = " ".join(a.lower() for a in answers)
    return [term for term in _GENERIC_TERMS if term in text]


def quantified_claim_count(answers: list[str]) -> int:
    count = 0
    for answer in answers:
        if _QUANT_RE.search(answer) or _QUANT_VERB_RE.search(answer):
            count += 1
    return count


def validate_answers(answers: list[str]) -> dict:
    """Authenticity signals for the candidate's answers so far."""
    repeated = repeated_phrases(answers)
    generic = generic_term_hits(answers)
    quantified = quantified_claim_count(answers)

    score = 8.0
    score -= min(3.0, 1.0 * len(repeated))
    score -= min(2.0, 0.5 * len(generic))
    if quantified >= 1:
        score += 1.0
    if quantified >= 3:
        score += 1.0
    score = round(max(1.0, min(10.0, score)), 1)

    return {
        "answer_count": len(answers),
        "repeated_phrases": repeated,
        "generic_term_hits": generic,
        "quantified_claims": quantified,
        "has_quantified_evidence": quantified >= 1,
        "authenticity_score": score,
    }
