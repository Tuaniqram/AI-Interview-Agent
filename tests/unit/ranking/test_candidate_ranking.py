"""T3 — cross-candidate ranking helpers (calibrated + comparable)."""
from types import SimpleNamespace

import pytest

from app.api.v1.candidate_ranking import (
    _calibration_fields,
    _score_band,
    annotate_comparability,
    build_ranking_row,
    sort_rankings,
)


def _session(**overrides):
    base = {
        "id": "s-1",
        "job_role": "Marketing Manager",
        "final_score": 7.2,
        "started_at": None,
        "ended_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _candidate():
    return SimpleNamespace(
        id="c-1", name="Ada", email="ada@x.com", resume_url="/r", skills=["seo"]
    )


def _dept():
    return SimpleNamespace(id=3, name="Growth")


def test_build_ranking_row_detects_family_and_calibration():
    row = build_ranking_row(
        _session(),
        _candidate(),
        _dept(),
        weighted_score=6.8,
        calibration_fields={
            "calibrated_score": 7.6,
            "difficulty_reached": 4,
            "role_floor": 3,
        },
    )
    assert row["family"] == "marketing"
    assert row["calibrated_score"] == 7.6
    assert row["difficulty_reached"] == 4
    assert row["role_floor"] == 3
    assert row["score_band"] == "hire"
    assert row["final_score"] == 7.2
    assert row["weighted_score"] == 6.8
    assert row["comparable_note"] is None


def test_build_ranking_row_defaults_technical_when_role_unknown():
    row = build_ranking_row(_session(job_role="Mystery Role"), _candidate(), _dept(), None, {})
    assert row["family"] == "technical"
    assert row["calibrated_score"] is None
    assert row["score_band"] is None


def test_calibration_fields_falls_back_to_difficulty_state():
    fields = _calibration_fields(
        {
            "calibration_state": {"calibrated_verdict": "hire"},
            "difficulty_state": {"difficulty_reached": 5, "role_floor": 4},
        }
    )
    assert fields["difficulty_reached"] == 5
    assert fields["role_floor"] == 4
    assert fields["calibrated_score"] is None


def test_score_band_boundaries():
    assert _score_band(8.5) == "strong_hire"
    assert _score_band(7.5) == "hire"
    assert _score_band(6.5) == "lean_hire"
    assert _score_band(6.0) == "concern"
    assert _score_band(None) is None


def test_annotate_comparability_notes_out_of_cohort_family():
    rows = [
        {"family": "marketing", "comparable_note": None},
        {"family": "marketing", "comparable_note": None},
        {"family": "finance", "comparable_note": None},
    ]
    out = annotate_comparability(rows)
    assert out[0]["comparable_note"] is None
    assert out[1]["comparable_note"] is None
    assert "finance" in out[2]["comparable_note"]


def test_sort_rankings_calibrated_desc_nulls_last():
    rows = [
        {"final_score": 9.0, "calibrated_score": None},
        {"final_score": 8.0, "calibrated_score": 7.2},
        {"final_score": 8.5, "calibrated_score": 8.1},
        {"final_score": 7.0, "calibrated_score": 6.0},
    ]
    out = sort_rankings(rows, sort_by="calibrated")
    assert [r["calibrated_score"] for r in out] == [8.1, 7.2, 6.0, None]


def test_sort_rankings_final_is_default():
    rows = [
        {"final_score": 6.0, "calibrated_score": 9.0},
        {"final_score": 9.0, "calibrated_score": 5.0},
    ]
    out = sort_rankings(rows)
    assert out[0]["final_score"] == 9.0
