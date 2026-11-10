from app.services.feedback_text import legacy_to_plain, plain_feedback


def test_plain_feedback_never_exposes_engine_terms():
    text = plain_feedback("insufficient_evidence", 0.0, 3, 3)
    assert "insufficient_evidence" not in text
    assert "confidence" not in text.lower()
    assert "not give us enough evidence" in text
    assert "You answered 3 questions." in text
    assert "3 pieces of evidence" in text


def test_plain_feedback_uses_singular_counts():
    text = plain_feedback("no_hire", 0.9, 1, 1)
    assert "You answered 1 question." in text
    assert "One piece of evidence was recorded" in text


def test_legacy_feedback_is_rewritten_for_existing_records():
    legacy = "Verdict: insufficient_evidence (confidence 0.00). Questions asked: 3. Evidence collected: 3."
    text = legacy_to_plain(legacy)
    assert text is not None
    assert "Verdict:" not in text
    assert "insufficient_evidence" not in text
    assert "early signal" in text


def test_existing_plain_feedback_and_empty_values_are_unchanged():
    assert legacy_to_plain("Your interview went well.") == "Your interview went well."
    assert legacy_to_plain(None) is None
