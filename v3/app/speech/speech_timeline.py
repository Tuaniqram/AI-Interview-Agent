from app.speech.models import (
    VisemeEvent,
    ExpressionEvent,
    GestureEvent,
    GestureHint,
    EmotionType,
)
from app.speech.viseme_generator import generate_viseme_timeline


def build_speech_timeline(
    text: str,
    emotion: EmotionType = EmotionType.neutral,
    timestamps: list[dict] | None = None,
) -> dict:
    raw_visemes = generate_viseme_timeline(text, timestamps)
    viseme_events = [
        VisemeEvent(
            time=v["time"],
            value=v["value"],
            intensity=v["intensity"],
            duration=v["duration"],
        )
        for v in raw_visemes
    ]

    total_duration = (
        viseme_events[-1].time + viseme_events[-1].duration
        if viseme_events
        else len(text) * 0.08
    )

    expression_events: list[ExpressionEvent] = []
    if emotion != EmotionType.neutral:
        expression_events.append(
            ExpressionEvent(time=0.0, emotion=emotion, intensity=0.6)
        )
        expression_events.append(
            ExpressionEvent(time=total_duration * 0.5, emotion=emotion, intensity=0.4)
        )

    gesture_events: list[GestureEvent] = []
    sentence_boundaries = _find_sentence_boundaries(text)
    for boundary_time in sentence_boundaries:
        if boundary_time < total_duration * 0.8:
            gesture_events.append(
                GestureEvent(
                    time=boundary_time,
                    gesture=GestureHint.emphasis,
                    intensity=0.5,
                )
            )

    return {
        "duration": round(total_duration, 3),
        "visemes": [v.model_dump() for v in viseme_events],
        "expressions": [e.model_dump() for e in expression_events],
        "gestures": [g.model_dump() for g in gesture_events],
    }


def _find_sentence_boundaries(text: str) -> list[float]:
    words = text.split()
    total_chars = len(text)
    boundaries: list[float] = []
    char_count = 0

    for i, word in enumerate(words):
        char_count += len(word) + 1
        if word.endswith((".", "!", "?")) and i < len(words) - 1:
            t = (char_count / total_chars) * (len(words) * 0.3)
            boundaries.append(round(t, 3))

    return boundaries
