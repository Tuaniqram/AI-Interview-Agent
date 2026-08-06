"""V5 question memory — semantic duplicate prevention (AURA hardening).

Keeps a short memory of the last questions asked and rejects a new question
that is too close to one already asked. Two layers, both dependency-free and
deterministic:

1. Lexical similarity — bigram Jaccard + token-overlap, rejects near-verbatim
   duplicates (``similarity > DUPLICATE_SIMILARITY_THRESHOLD``).
2. Topic memory — keyword-sets per recurring interview topic; a new question
   sharing two or more topics with a single previous question is treated as a
   repeat (the classic "scalability / performance / LLM volume" loop), unless
   the caller opts into a new dimension.

Pure functions: no LLM, no DB, no shared state.
"""
import re

DUPLICATE_SIMILARITY_THRESHOLD = 0.8
MEMORY_SIZE = 10

_STOP = {
    "how", "what", "why", "would", "did", "do", "does", "you", "your", "the",
    "a", "an", "and", "or", "if", "when", "can", "could", "about", "tell",
    "describe", "walk", "share", "example", "time", "question", "me",
}

TOPIC_KEYWORDS = {
    "scalability": {"scal", "load", "traffic", "concurr", "throughput", "volume", "capacity", "peak"},
    "performance": {"perform", "latency", "slow", "degrad", "optimiz", "bottleneck"},
    "llm_integration": {"llm", "model", "prompt", "token", "inference", "generation"},
    "architecture": {"architect", "design", "microservice", "monolith", "trade-off", "tradeoff", "component", "module"},
    "caching": {"cache", "invalidation", "ttl", "memcached", "redis"},
    "database": {"database", "sql", "query", "index", "schema", "storage", "replica"},
    "security": {"secur", "auth", "vulnerab", "threat", "encrypt", "oauth"},
    "testing": {"test", "qa", "coverage", "debug", "regression"},
    "cloud_infra": {"kubernetes", "docker", "deploy", "infrastructure", "aws", "gcp", "cloud"},
    "communication": {"explain", "stakeholder", "communicat", "present", "document"},
    "leadership": {"lead", "team", "mentor", "influence", "conflict", "ownership"},
    "problem_solving": {"problem", "debug", "incident", "fail", "resolve", "diagnos"},
    "trade_offs": {"trade-off", "tradeoff", "pros", "cons", "compromise", "decid"},
}

__all__ = [
    "DUPLICATE_SIMILARITY_THRESHOLD",
    "MEMORY_SIZE",
    "TOPIC_KEYWORDS",
    "semantic_similarity",
    "match_topics",
    "recent_memory",
    "check_duplicate",
    "avoid_topics_summary",
]


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in _STOP]


def semantic_similarity(a: str, b: str) -> float:
    """Deterministic 0..1 similarity between two questions.

    Max of bigram Jaccard and token overlap — bigrams catch shared phrasing,
    token overlap catches shared keywords in different order.
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    bigrams_a = set(zip(ta, ta[1:]))
    bigrams_b = set(zip(tb, tb[1:]))
    if bigrams_a and bigrams_b:
        bigram_score = len(bigrams_a & bigrams_b) / len(bigrams_a | bigrams_b)
    else:
        bigram_score = 0.0
    sa, sb = set(ta), set(tb)
    overlap = len(sa & sb) / max(len(sa), len(sb)) if sa | sb else 0.0
    return max(bigram_score, overlap)


def match_topics(text: str) -> set[str]:
    """Topics (from ``TOPIC_KEYWORDS``) referenced by a question."""
    lowered = (text or "").lower()
    return {name for name, kws in TOPIC_KEYWORDS.items() if any(kw in lowered for kw in kws)}


def recent_memory(questions_asked: list[dict]) -> list[str]:
    """The last ``MEMORY_SIZE`` question texts."""
    texts = [
        str(q.get("text", "")).strip()
        for q in (questions_asked or [])
        if str(q.get("text", "")).strip()
    ]
    return texts[-MEMORY_SIZE:]


def check_duplicate(
    question: str,
    memory: list[str],
    *,
    similarity_threshold: float = DUPLICATE_SIMILARITY_THRESHOLD,
) -> tuple[bool, dict]:
    """Reject a question that repeats a recent one.

    Returns ``(is_duplicate, detail)`` where detail explains the rejection:
    ``{"kind": "similar", "against": <text>, "similarity": float}`` or
    ``{"kind": "topic_repeat", "against": <text>, "topics": [...]}``.
    """
    question = (question or "").strip()
    if not question or not memory:
        return False, {}

    q_topics = match_topics(question)

    for prev in memory:
        similarity = semantic_similarity(question, prev)
        if similarity > similarity_threshold:
            return True, {
                "kind": "similar",
                "against": prev,
                "similarity": round(similarity, 4),
            }

    if len(q_topics) >= 2:
        for prev in memory:
            shared = q_topics & match_topics(prev)
            if len(shared) >= 2:
                return True, {
                    "kind": "topic_repeat",
                    "against": prev,
                    "topics": sorted(shared),
                }

    return False, {}


def avoid_topics_summary(memory: list[str]) -> str:
    """Topics already covered, for the generator to steer away from."""
    topics: set[str] = set()
    for text in memory:
        topics |= match_topics(text)
    if not topics:
        return "None"
    return ", ".join(sorted(topics))
