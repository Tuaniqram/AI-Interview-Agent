"""V5 information-gain selection — the target-selection capability.

Scores how much probing each hypothesis would reveal (the Shannon entropy of
its posterior belief) and picks the argmax, preserving the legacy coverage
priority (untested = max entropy) and the deep-probe fallback. Pure and
stateless.
"""
import math

DEEP_PROBE_CONFIRMED_FLOOR = 0.9  # above this, a confirmed hypothesis is settled

__all__ = [
    "DEEP_PROBE_CONFIRMED_FLOOR",
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
    coverage). Refuted hypotheses never get re-probed (0.0), and confirmed
    hypotheses near-certain (>= DEEP_PROBE_CONFIRMED_FLOOR) are treated as
    settled. Everything else scores by the entropy of its posterior — the more
    uncertain a belief is, the more a question about it is expected to reveal.
    """
    status = hypothesis.get("status", "untested")
    if status == "refuted":
        return 0.0
    if status == "untested":
        return 1.0
    confidence = float(hypothesis.get("confidence", 0.5) or 0.0)
    p = max(0.0, min(1.0, confidence))
    if status == "confirmed" and p >= DEEP_PROBE_CONFIRMED_FLOOR:
        return 0.0
    return round(_entropy(p), 4)


def next_target(hypotheses: list[dict]) -> dict | None:
    """Pick the hypothesis that maximizes expected information gain.

    Generalizes the old tiered rule (untested → most_uncertain → deep_probe):
    untested hypotheses carry max EIG (1.0) so coverage still wins; among
    probed hypotheses the one closest to p=0.5 (max entropy) wins; confirmed
    hypotheses only when nothing more uncertain remains. The returned target
    carries the EIG score plus a human-readable `selection_reason`.
    """
    if not hypotheses:
        return None

    candidates = [h for h in hypotheses if h.get("status") != "refuted"]
    if not candidates:
        return None

    # max() keeps the first element on ties, so equal-EIG hypotheses (e.g. all
    # untested at 1.0) preserve list order — untested coverage stays stable.
    best = max(candidates, key=expected_information_gain)
    best_score = expected_information_gain(best)

    if best_score > 0.0:
        result = dict(best)
        result["selection_reason"] = (
            "untested" if best.get("status") == "untested" else "max_information_gain"
        )
    else:
        # Nothing productive remains (everything settled or degenerate) — keep
        # the legacy deep-probe behavior: drill into the strongest hypothesis.
        result = dict(max(candidates, key=lambda h: (h.get("confidence", 0.0) or 0.0)))
        result["selection_reason"] = "deep_probe"

    result["information_gain"] = round(best_score, 4)
    return result
