"""V5 information-gain selection — the target-selection capability.

Scores how much probing each hypothesis would reveal (the Shannon entropy of
its posterior belief) and picks the argmax, preserving the legacy coverage
priority (untested = max entropy) and the deep-probe fallback. Pure and
stateless.
"""
import math

DEEP_PROBE_CONFIRMED_FLOOR = 0.9  # above this, a confirmed hypothesis is settled

# Statuses that carry no further information — never re-probed (AURA V5:
# confirmed beliefs are decided, refuted beliefs are decided, saturated
# hypotheses yielded no new information after enough probing).
SETTLED_STATUSES = ("confirmed", "refuted", "saturated")

__all__ = [
    "DEEP_PROBE_CONFIRMED_FLOOR",
    "SETTLED_STATUSES",
    "_entropy",
    "expected_information_gain",
    "next_target",
]


def _entropy(p: float) -> float:
    """Shannon entropy (bits) of a Bernoulli posterior with probability p."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def expected_information_gain(hypothesis: dict) -> float:
    """Expected information gain (V1) ≈ current uncertainty of the hypothesis.

    Untested hypotheses sit at the max-entropy prior and score 1.0 (guaranteed
    coverage). Settled hypotheses — refuted, saturated, or confirmed near-certain
    (>= DEEP_PROBE_CONFIRMED_FLOOR) — never get re-probed (0.0). Everything else
    scores by the entropy of its posterior — the more uncertain a belief is,
    the more a question about it is expected to reveal.
    """
    status = hypothesis.get("status", "untested")
    if status in ("refuted", "saturated"):
        return 0.0
    if status == "untested":
        return 1.0
    confidence = float(hypothesis.get("confidence", 0.5) or 0.0)
    p = max(0.0, min(1.0, confidence))
    if status == "confirmed" and p >= DEEP_PROBE_CONFIRMED_FLOOR:
        return 0.0
    return round(_entropy(p), 4)


def next_target(
    hypotheses: list[dict],
    exclude_ids: list[str] | set[str] | None = None,
    planned_competency: str | None = None,
    competency_coverage: dict | None = None,
) -> dict | None:
    """Pick the open hypothesis that maximizes expected information gain.

    Saturation (AURA V5): hypotheses whose status is settled (``confirmed``,
    ``refuted`` or ``saturated``) are never re-probed — once a belief is decided
    (or probing stopped yielding new information), the interview moves on.
    ``exclude_ids`` adds a same-target cooldown (the most recently probed
    hypothesis is skipped so coverage rotates instead of looping), and
    ``planned_competency`` scopes selection to a single competency when the
    planner just rotated to it.

    Untested hypotheses carry max EIG (1.0) so coverage still wins; among equal
    EIG scores, the hypothesis in the least-covered competency (per
    ``competency_coverage``) wins so the interview rotates across areas instead
    of drilling one forever. When nothing open remains the interview is
    saturated — returns ``None`` (the engine rotates competencies or finishes).
    """
    if not hypotheses:
        return None

    exclude_ids = set(exclude_ids or [])
    candidates = [
        h for h in hypotheses
        if h.get("status") not in SETTLED_STATUSES
        and h.get("id") not in exclude_ids
    ]
    if planned_competency:
        scoped = [h for h in candidates if h.get("competency") == planned_competency]
        if scoped:
            candidates = scoped
    if not candidates:
        return None

    coverage = competency_coverage or {}

    def _rank(h: dict) -> tuple[float, int]:
        return (expected_information_gain(h), -int(coverage.get(h.get("competency", ""), 0) or 0))

    # max() keeps the first element on full ties, so equal-EIG hypotheses (e.g.
    # all untested at 1.0 with equal coverage) preserve list order — untested
    # coverage stays stable.
    best = max(candidates, key=_rank)
    best_score = expected_information_gain(best)

    result = dict(best)
    result["selection_reason"] = (
        "untested" if best.get("status") == "untested" else "max_information_gain"
    )
    result["information_gain"] = round(best_score, 4)
    return result
