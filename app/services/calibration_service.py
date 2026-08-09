"""T4 calibration loop — measure and report drift (deterministic).

The predicted side of a session (calibrated verdict/score, difficulty reached,
role floor) is already persisted in ``interview_brain.brain_metadata`` at
finalize. Recruiters record the actual post-hire outcome against a session;
this module reconciles the two and reports drift (correct / over-predicted /
under-predicted) per job family and difficulty-credit band.

Pure functions only — no DB, no LLM, no auto-tuning. Testable in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass

# Actual post-hire outcomes recruiters may record against a session.
ACTUAL_OUTCOMES: tuple[str, ...] = (
    "strong_performance",
    "met_expectations",
    "below_expectations",
    "terminated_during_probation",
    "no_feedback",
)

# Calibrated verdict -> coarse prediction bucket.
_PREDICTED_BUCKET: dict[str, str] = {
    "strong_hire": "hire",
    "hire": "hire",
    "lean_hire": "lean_hire",
    "insufficient_evidence": "uncertain",
    "borderline": "uncertain",
    "review": "uncertain",
    "lean_no_hire": "no_hire",
    "no_hire": "no_hire",
    "strong_no_hire": "no_hire",
}

# Actual outcome -> coarse performance bucket.
_ACTUAL_BUCKET: dict[str, str] = {
    "strong_performance": "hire",
    "met_expectations": "lean_hire",
    "below_expectations": "no_hire",
    "terminated_during_probation": "no_hire",
    "no_feedback": "uncertain",
}

_BUCKET_ORDER: dict[str, int] = {"hire": 2, "lean_hire": 1, "no_hire": 0}


def predicted_bucket(verdict: str | None) -> str:
    """Coarse bucket ('hire' / 'lean_hire' / 'no_hire' / 'uncertain') of a verdict."""
    return _PREDICTED_BUCKET.get(str(verdict or "").lower(), "uncertain")


def actual_bucket(outcome: str | None) -> str:
    """Coarse performance bucket of a recorded outcome."""
    return _ACTUAL_BUCKET.get(str(outcome or "").lower(), "uncertain")


def classify_prediction(predicted_verdict: str | None, actual_outcome: str | None) -> str:
    """'correct' | 'over_predict' | 'under_predict' | 'uncertain'."""
    pb = predicted_bucket(predicted_verdict)
    ab = actual_bucket(actual_outcome)
    if pb == "uncertain" or ab == "uncertain":
        return "uncertain"
    if pb == ab:
        return "correct"
    return (
        "over_predict"
        if _BUCKET_ORDER[pb] > _BUCKET_ORDER[ab]
        else "under_predict"
    )


def difficulty_credit(difficulty_reached, role_floor) -> float:
    """Difficulty credit mirroring ``app/brain/calibration.py``.

    Credit is a strict function of how far past the role floor (if any) the
    session reached. Deep sessions get positive credit; missing the floor is
    penalized.
    """
    try:
        reached = int(difficulty_reached or 0)
    except (TypeError, ValueError):
        reached = 0
    try:
        floor = int(role_floor) if role_floor is not None else None
    except (TypeError, ValueError):
        floor = None
    if floor is not None:
        if reached >= floor:
            return min(0.4, 0.1 * (reached - floor + 1))
        return -0.4
    return min(0.3, 0.1 * max(0, reached - 1))


def difficulty_band(difficulty_reached, role_floor) -> str:
    """Coarse credit band used to bucket drift reporting."""
    credit = difficulty_credit(difficulty_reached, role_floor)
    if credit >= 0.3:
        return ">=0.3 (deep)"
    if credit >= 0.1:
        return "0.1-0.3"
    if credit >= 0.0:
        return "0-0.1"
    return "floor unmet"


def _ratio(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


@dataclass
class _BucketStats:
    total: int = 0
    matched: int = 0
    correct: int = 0
    over: int = 0
    under: int = 0


def _accumulate(stats: _BucketStats, classification: str) -> None:
    stats.total += 1
    if classification == "uncertain":
        return
    stats.matched += 1
    if classification == "correct":
        stats.correct += 1
    elif classification == "over_predict":
        stats.over += 1
    elif classification == "under_predict":
        stats.under += 1


def _series(rows: list[dict], stats: _BucketStats) -> dict:
    return {
        "total": stats.total,
        "matched": stats.matched,
        "correct": stats.correct,
        "over_predictions": stats.over,
        "under_predictions": stats.under,
        "correctness_rate": _ratio(stats.correct, stats.matched),
        "over_prediction_rate": _ratio(stats.over, stats.matched),
        "under_prediction_rate": _ratio(stats.under, stats.matched),
    }


def build_drift_report(feedback: list[dict]) -> dict:
    """Reconcile predicted vs actual across sessions.

    ``feedback`` items carry ``job_role``, ``predicted_verdict``,
    ``actual_outcome``, ``difficulty_reached``, ``role_floor`` (family resolved
    by the caller via ``detect_family``).
    """
    overall = _BucketStats()
    by_family: dict[str, _BucketStats] = {}
    by_band: dict[str, _BucketStats] = {}

    for row in feedback:
        classification = classify_prediction(
            row.get("predicted_verdict"), row.get("actual_outcome")
        )
        _accumulate(overall, classification)

        family = str(row.get("family") or "technical")
        by_family.setdefault(family, _BucketStats())
        _accumulate(by_family[family], classification)

        band = difficulty_band(row.get("difficulty_reached"), row.get("role_floor"))
        by_band.setdefault(band, _BucketStats())
        _accumulate(by_band[band], classification)

    return {
        "overall": _series(feedback, overall),
        "by_family": {
            fam: _series([], stats)
            for fam, stats in sorted(by_family.items())
        },
        "by_difficulty_band": {
            band: _series([], stats)
            for band, stats in sorted(by_band.items())
        },
        "insights": _insights(overall, by_family, by_band),
    }


def build_drift_summary(feedback: list[dict]) -> dict:
    """Headline numbers: tracked, awaiting feedback, agreement, drift counts."""
    overall = _BucketStats()
    awaiting = 0
    for row in feedback:
        classification = classify_prediction(
            row.get("predicted_verdict"), row.get("actual_outcome")
        )
        if str(row.get("actual_outcome") or "").lower() == "no_feedback":
            awaiting += 1
        _accumulate(overall, classification)
    return {
        "tracked_sessions": overall.total,
        "awaiting_feedback": awaiting,
        "with_feedback": overall.total - awaiting,
        "matched": overall.matched,
        "correct": overall.correct,
        "over_predictions": overall.over,
        "under_predictions": overall.under,
        "correctness_rate": _ratio(overall.correct, overall.matched),
        "insights": _insights(overall, {}, {}),
    }


def _insights(
    overall: _BucketStats,
    by_family: dict[str, _BucketStats],
    by_band: dict[str, _BucketStats],
) -> list[str]:
    """Deterministic, plain-language drift notes. Empty when data is thin."""
    insights: list[str] = []
    if overall.matched < 3:
        return insights

    correctness = _ratio(overall.correct, overall.matched)
    if correctness < 0.6:
        insights.append(
            f"Low agreement: {correctness:.0%} of tracked sessions matched "
            "predicted outcome — calibration should be reviewed."
        )
    if overall.over >= 2 and overall.over >= overall.under * 1.5:
        insights.append(
            f"Systematically over-predicting: {overall.over} over vs "
            f"{overall.under} under. Verdicts skew more optimistic than "
            "post-hire outcomes."
        )
    elif overall.under >= 2 and overall.under >= overall.over * 1.5:
        insights.append(
            f"Systematically under-predicting: {overall.under} under vs "
            f"{overall.over} over. Qualified candidates are being missed."
        )

    for band, stats in by_band.items():
        if stats.matched >= 3 and _ratio(stats.over, stats.matched) > 0.5:
            insights.append(
                f"Difficulty credit band '{band}' over-predicts "
                f"{_ratio(stats.over, stats.matched):.0%} of the time — the "
                "credit may be inflating verdicts."
            )
    for fam, stats in by_family.items():
        if stats.matched >= 3 and _ratio(stats.over, stats.matched) > 0.5:
            insights.append(
                f"Family '{fam}' over-predicts "
                f"{_ratio(stats.over, stats.matched):.0%} of the time."
            )
    return insights
