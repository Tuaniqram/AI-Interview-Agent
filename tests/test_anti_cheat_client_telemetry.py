"""Browser-supplied integrity telemetry can only add suspicion, never remove it.

The telemetry (paste size, focus loss, keystroke rhythm, pointer leaves, heartbeat gaps) comes from the candidate's own
browser, so a candidate can send anything. These tests pin the property that makes that safe: a "clean" report scores
exactly like sending nothing, so forging it gains nothing, and the signals the server observes itself (answer latency,
text style, duplicates) always stand.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services import anti_cheat

CLEAN = {
    "paste_chars": 0,
    "focus_lost_count": 0,
    "pointer_leaves": 0,
    "heartbeat_gaps": 0,
    "answer_source": "typing",
    # slow, irregular human-looking key gaps (milliseconds)
    "keystroke_intervals": [180, 240, 150, 310, 205, 260, 170, 290, 220, 195] * 6,
    "first_key_ms": 900,
}

ANSWER = (
    "My previous role required balancing competing priorities because the organization was scaling quickly across "
    "multiple regions and teams. I introduced a structured review process to align stakeholders and then measured "
    "the outcome of that process over a full quarter."
)


def _settings(judge: bool = False):
    return SimpleNamespace(
        ANTI_CHEAT_GUARD_ENABLED=True, ANTI_CHEAT_LLM_JUDGE=judge, ANTI_CHEAT_FLAG_THRESHOLD=70,
        ANTI_CHEAT_MAX_FLAGS=3, ANTI_CHEAT_ANSWER_TIME_LIMIT_S=120, ANTI_CHEAT_POINTER_LEAVE_THRESHOLD=3,
        ANTI_CHEAT_TAMPER_DIVERGENCE_S=0.5,
    )


def _asked(seconds_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()


@pytest.mark.parametrize("seconds_ago", [0.0, 5.0, 90.0, 600.0])
async def test_clean_telemetry_scores_the_same_as_no_telemetry(monkeypatch, seconds_ago):
    monkeypatch.setattr("app.services.anti_cheat.settings", _settings())
    asked = _asked(seconds_ago)
    without = await anti_cheat.assess(text=ANSWER, question_asked_at=asked)
    with_clean = await anti_cheat.assess(text=ANSWER, question_asked_at=asked, **CLEAN)
    assert with_clean["score"] == without["score"], (with_clean, without)
    assert with_clean["flagged"] == without["flagged"]


@pytest.mark.parametrize("seconds_ago", [4.0, 12.0, 25.0, 45.0])
async def test_clean_telemetry_does_not_dilute_a_judged_score(monkeypatch, seconds_ago):
    """With the LLM judge on, the score is a blend, so a "clean" signal that joined the average would lower it."""
    monkeypatch.setattr("app.services.anti_cheat.settings", _settings(judge=True))

    async def judge(text, question):
        return 90, ["reads machine-generated"]

    monkeypatch.setattr(anti_cheat, "llm_judge", judge)
    asked = _asked(seconds_ago)
    without = await anti_cheat.assess(text=ANSWER, question_asked_at=asked)
    with_clean = await anti_cheat.assess(text=ANSWER, question_asked_at=asked, **CLEAN)
    assert with_clean["score"] == without["score"], (with_clean["score"], without["score"])


async def test_instant_answer_stays_flagged_whatever_the_browser_reports(monkeypatch):
    monkeypatch.setattr("app.services.anti_cheat.settings", _settings())
    result = await anti_cheat.assess(text=ANSWER, question_asked_at=_asked(0.0), **CLEAN)
    assert result["flagged"] is True  # the server saw the answer arrive instantly
    assert any("too fast" in r for r in result["reasons"])


async def test_duplicate_of_an_earlier_answer_stays_flagged_with_clean_telemetry(monkeypatch):
    monkeypatch.setattr("app.services.anti_cheat.settings", _settings())
    result = await anti_cheat.assess(
        text=ANSWER, question_asked_at=_asked(600.0), prior_answers=[ANSWER], **CLEAN,
    )
    assert result["flagged"] is True


async def test_real_suspicious_telemetry_still_adds_to_the_score(monkeypatch):
    monkeypatch.setattr("app.services.anti_cheat.settings", _settings())
    asked = _asked(600.0)
    quiet = await anti_cheat.assess(text=ANSWER, question_asked_at=asked)
    noisy = await anti_cheat.assess(
        text=ANSWER, question_asked_at=asked, paste_chars=400, focus_lost_count=3, heartbeat_gaps=2,
    )
    assert noisy["score"] > quiet["score"]
