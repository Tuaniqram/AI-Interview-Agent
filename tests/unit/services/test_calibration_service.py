"""T4 calibration loop — deterministic drift math (pure functions)."""
import pytest

from app.services.calibration_service import (
    ACTUAL_OUTCOMES,
    classify_prediction,
    difficulty_band,
    difficulty_credit,
    build_drift_report,
    build_drift_summary,
)


def test_actual_outcomes_are_stable():
    assert ACTUAL_OUTCOMES == (
        "strong_performance",
        "met_expectations",
        "below_expectations",
        "terminated_during_probation",
        "no_feedback",
    )


@pytest.mark.parametrize(
    ("predicted", "actual", "expected"),
    [
        ("hire", "strong_performance", "correct"),
        ("strong_hire", "met_expectations", "over_predict"),
        ("hire", "below_expectations", "over_predict"),
        ("hire", "terminated_during_probation", "over_predict"),
        ("lean_no_hire", "met_expectations", "under_predict"),
        ("no_hire", "strong_performance", "under_predict"),
        ("lean_hire", "met_expectations", "correct"),
        ("no_hire", "below_expectations", "correct"),
        # Non-committal predictions never count as correct/incorrect.
        ("insufficient_evidence", "strong_performance", "uncertain"),
        ("borderline", "met_expectations", "uncertain"),
        ("no_hire", "no_feedback", "uncertain"),
        # Unknown input is tolerated and never crashes.
        (None, "met_expectations", "uncertain"),
        ("hire", None, "uncertain"),
        ("HIRE", "below_expectations", "over_predict"),
    ],
)
def test_classify_prediction(predicted, actual, expected):
    assert classify_prediction(predicted, actual) == expected


def test_difficulty_credit_floor_satisfied_scales():
    assert difficulty_credit(3, 3) == pytest.approx(0.1)
    assert difficulty_credit(4, 3) == pytest.approx(0.2)
    assert difficulty_credit(6, 3) == pytest.approx(0.4)  # capped at 0.4


def test_difficulty_credit_floor_unmet_is_penalized():
    assert difficulty_credit(2, 3) == pytest.approx(-0.4)


def test_difficulty_credit_no_floor_ramps_to_0_3():
    assert difficulty_credit(1, None) == pytest.approx(0.0)
    assert difficulty_credit(2, None) == pytest.approx(0.1)
    assert difficulty_credit(4, None) == pytest.approx(0.3)  # capped at 0.3


def test_difficulty_credit_tolerates_garbage():
    assert difficulty_credit(None, None) == pytest.approx(0.0)
    assert difficulty_credit("x", "y") == pytest.approx(0.0)


def test_difficulty_bands():
    assert difficulty_band(1, None) == "0-0.1"
    assert difficulty_band(2, None) == "0.1-0.3"
    assert difficulty_band(4, None) == ">=0.3 (deep)"
    assert difficulty_band(2, 3) == "floor unmet"


def _row(**overrides):
    row = {
        "job_role": "Marketing Manager",
        "family": "marketing",
        "predicted_verdict": "hire",
        "actual_outcome": "strong_performance",
        "difficulty_reached": 4,
        "role_floor": 3,
    }
    row.update(overrides)
    return row


def test_build_drift_report_buckets_family_and_band():
    report = build_drift_report([
        _row(job_role="Marketing Manager", family="marketing"),
        _row(job_role="Finance Analyst", family="finance",
             predicted_verdict="no_hire", actual_outcome="below_expectations"),
        _row(job_role="Marketing Manager", family="marketing",
             predicted_verdict="hire", actual_outcome="below_expectations"),
    ])
    overall = report["overall"]
    assert overall["total"] == 3
    assert overall["matched"] == 3
    assert overall["correct"] == 2
    assert overall["over_predictions"] == 1
    assert overall["under_predictions"] == 0
    assert overall["correctness_rate"] == pytest.approx(2 / 3, abs=1e-4)

    fam = report["by_family"]
    assert fam["marketing"]["total"] == 2
    assert fam["marketing"]["over_predictions"] == 1
    assert fam["finance"]["correct"] == 1

    bands = report["by_difficulty_band"]
    assert "0.1-0.3" in bands


def test_build_drift_report_uncertain_excluded_from_correctness():
    report = build_drift_report([
        _row(predicted_verdict="borderline", actual_outcome="strong_performance"),
        _row(predicted_verdict="hire", actual_outcome="no_feedback"),
        _row(predicted_verdict="hire", actual_outcome="strong_performance"),
    ])
    overall = report["overall"]
    assert overall["total"] == 3
    assert overall["matched"] == 1
    assert overall["correct"] == 1
    assert overall["correctness_rate"] == 1.0


def test_insights_fire_on_structural_over_prediction():
    rows = []
    # 4 hires, all underperform -> low agreement + over-prediction insight.
    for outcome in ("below_expectations",) * 4:
        rows.append(_row(predicted_verdict="strong_hire", actual_outcome=outcome))
    rows.append(_row(predicted_verdict="hire", actual_outcome="strong_performance"))
    report = build_drift_report(rows)
    joined = " ".join(report["insights"])
    assert "over-predicting" in joined
    assert "calibration should be reviewed" in joined


def test_insights_empty_on_thin_data():
    report = build_drift_report([
        _row(predicted_verdict="hire", actual_outcome="strong_performance"),
    ])
    assert report["insights"] == []


def test_build_drift_summary_counts_awaiting():
    summary = build_drift_summary([
        _row(actual_outcome="strong_performance"),
        _row(actual_outcome="no_feedback"),
        _row(actual_outcome="below_expectations"),
    ])
    assert summary["tracked_sessions"] == 3
    assert summary["awaiting_feedback"] == 1
    assert summary["with_feedback"] == 2
    assert summary["correct"] == 1
    assert summary["over_predictions"] == 1
