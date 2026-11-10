"""Plain-language candidate feedback.

The engine stores one short feedback string per completed session. It is shown
to candidates, so it must never expose internal enums, probabilities or counts
as machine text. Older sessions were written as
``Verdict: <enum> (confidence 0.00). Questions asked: N. Evidence collected: M.``;
``legacy_to_plain`` rewrites those on read so they are readable without a
database migration.
"""
import re
from typing import Optional

PLAIN_VERDICTS = {
    "strong_hire": "Your interview went very well.",
    "hire": "Your interview went well.",
    "lean_hire": "Your interview went reasonably well.",
    "insufficient_evidence": "This interview did not give us enough evidence to reach a firm conclusion.",
    "lean_no_hire": "Your interview raised a few concerns.",
    "no_hire": "Your interview raised some concerns.",
    "strong_no_hire": "Your interview raised serious concerns.",
}

_LEGACY = re.compile(
    r"^Verdict:\s*(?P<verdict>[a-zA-Z_]+)\s*\(confidence\s*(?P<confidence>[0-9.]+)\)\.\s*"
    r"Questions asked:\s*(?P<questions>\d+)\.\s*"
    r"Evidence collected:\s*(?P<evidence>\d+)\.",
)


def plain_feedback(
    verdict: str,
    confidence: float,
    questions_asked: int,
    evidence_count: int,
) -> str:
    """A short, candidate-facing summary with no internal enum or ratio text."""
    sentences = [PLAIN_VERDICTS.get(verdict, "Your interview has been assessed.")]

    question_word = "question" if questions_asked == 1 else "questions"
    if evidence_count == 1:
        evidence_sentence = "One piece of evidence was recorded from your answers."
    else:
        evidence_sentence = (
            f"{evidence_count} pieces of evidence were recorded from your answers."
        )
    sentences.append(f"You answered {questions_asked} {question_word}. {evidence_sentence}")

    if confidence < 0.5:
        sentences.append("This result is an early signal rather than a full assessment.")
    return " ".join(sentences)


def legacy_to_plain(text: Optional[str]) -> Optional[str]:
    """Rewrite an older machine-readable feedback string in place, or return it unchanged."""
    if not text:
        return text
    match = _LEGACY.match(text.strip())
    if not match:
        return text
    return plain_feedback(
        match.group("verdict"),
        float(match.group("confidence")),
        int(match.group("questions")),
        int(match.group("evidence")),
    )
