import json
import logging
import re

from app.core.interview_state import InterviewState
from app.config.interview_styles import get_style
from app.agents.reasoning.evidence_engine import complexity_signal

logger = logging.getLogger(__name__)

MIN_SCORE = 1
MAX_SCORE = 5


def max_difficulty_reached(state: dict) -> int:
    """Highest difficulty level reached this session (B3).

    ``difficulty_level`` is the *current* level and can drop after a tough
    stretch, so reporting it as ``difficulty_reached`` understated the peak
    (the timeline hit 5 on Q8–Q11 while ``difficulty_state`` said 3). Prefer
    the governor's monotonic ``max_difficulty_reached`` and fall back to the
    current level for states that never passed through it.
    """
    tracked = state.get("max_difficulty_reached")
    try:
        if tracked is not None:
            return int(tracked)
    except (TypeError, ValueError):
        pass
    try:
        return int(state.get("difficulty_level") or 1)
    except (TypeError, ValueError):
        return 1


def _extract_json_object(text: str) -> dict:
    """Parse a JSON object from an LLM response that may carry prose or fences.

    Groq's cheap tier frequently appends text after the JSON object (or wraps
    it in a code fence), which made the naive ``json.loads`` fail on every
    turn and silently disabled the LLM governor. Tries, in order: the raw
    text, the text with a ```json fence stripped, the first balanced
    ``{...}`` object, and finally a ``"delta"`` regex when the object itself
    is unparseable.
    """
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break

    match = re.search(r'"delta"\s*:\s*(-?[0-9]+)\b', text)
    if match:
        return {"delta": int(match.group(1)), "rationale": "", "scaffold": ""}

    raise ValueError(f"no JSON object found in governor response: {text[:120]!r}")


# V5 6-dimension difficulty profile. Each dimension is scored 1-5 and
# described so the question generator can adapt *how* it asks, not just *how
# hard* the topic is.
DIFFICULTY_DIMENSIONS = [
    ("problem_complexity", "Problem complexity presented to the candidate"),
    ("abstraction_depth", "Level of abstraction the candidate must operate at"),
    ("time_pressure", "Implicit time pressure applied"),
    ("scaffolding_needed", "How much guidance the candidate is given (inverse)"),
    ("precision_required", "Precision and correctness demanded from answers"),
    ("follow_up_aggression", "Intensity of follow-up probing"),
]

_BASE_PROFILES = {
    1: {"problem_complexity": 1, "abstraction_depth": 1, "time_pressure": 1,
        "scaffolding_needed": 3, "precision_required": 1, "follow_up_aggression": 1},
    2: {"problem_complexity": 2, "abstraction_depth": 2, "time_pressure": 2,
        "scaffolding_needed": 2, "precision_required": 2, "follow_up_aggression": 2},
    3: {"problem_complexity": 3, "abstraction_depth": 3, "time_pressure": 3,
        "scaffolding_needed": 1, "precision_required": 3, "follow_up_aggression": 3},
    4: {"problem_complexity": 4, "abstraction_depth": 4, "time_pressure": 4,
        "scaffolding_needed": 1, "precision_required": 4, "follow_up_aggression": 4},
    5: {"problem_complexity": 5, "abstraction_depth": 5, "time_pressure": 5,
        "scaffolding_needed": 1, "precision_required": 5, "follow_up_aggression": 5},
}

# Once the interview is established and the last read was decisive, the LLM
# governor is skipped in favor of the cheap deterministic path.
DECISIVE_STATUSES = {"confirmed", "refuted"}
DECISIVE_PROBABILITY_BAND = (0.35, 0.65)  # outside this band a read is decisive


def should_skip_llm_governor(state: InterviewState) -> bool:
    """True when the deterministic path is good enough: mid-to-late interview
    plus a decisive last read (settled hypothesis or strong confidence)."""
    if int(state.get("question_number", 0) or 0) < 4:
        return False
    target = state.get("hypothesis_target") or {}
    status = target.get("status", "")
    if status in DECISIVE_STATUSES:
        return True
    confidence = float(target.get("confidence", 0.5) or 0.5)
    return not (DECISIVE_PROBABILITY_BAND[0] <= confidence <= DECISIVE_PROBABILITY_BAND[1])


def build_difficulty_profile(state: InterviewState, delta: int, rationale: str) -> dict:
    """Assemble the 6-dimension DifficultyProfile for the current level.

    Exposes both a structured ``dimensions`` list (name/value/description) and
    flat numeric keys (e.g. ``profile["abstraction_depth"]``) for ergonomic
    consumption by the question generator.
    """
    level = max(MIN_SCORE, min(MAX_SCORE, int(state.get("difficulty_level", 2) or 2)))
    base = dict(_BASE_PROFILES.get(level, _BASE_PROFILES[2]))

    # A delta toward harder pushes abstraction/precision up and scaffolding down.
    if delta > 0:
        base["abstraction_depth"] = min(4, base["abstraction_depth"] + 1)
        base["precision_required"] = min(4, base["precision_required"] + 1)
    elif delta < 0:
        base["problem_complexity"] = max(1, base["problem_complexity"] - 1)
        base["scaffolding_needed"] = min(4, base["scaffolding_needed"] + 1)

    profile = {
        "level": level,
        "delta": delta,
        "rationale": rationale,
        "dimensions": [
            {"name": name, "value": base[name], "description": description}
            for name, description in DIFFICULTY_DIMENSIONS
        ],
    }
    profile.update(base)
    return profile


def _evaluation_composite(state: InterviewState) -> float | None:
    """Average of the latest evaluation's scored dimensions (0..10)."""
    evaluation = state.get("unified_evaluation", {}) or {}
    scores = [
        data["score"]
        for data in evaluation.values()
        if isinstance(data, dict) and data.get("score") is not None
    ]
    if not scores:
        return None
    return sum(scores) / len(scores)


_ROLE_FLOOR_RULES = (
    (("principal", "staff", "lead", "architect"), 4),
    (("senior",), 3),
    (("mid", "intermediate", "regular"), 2),
    (("junior", "intern", "entry", "trainee", "graduate"), 1),
)


def role_difficulty_floor(job_role: str) -> int:
    """Minimum difficulty an interview must sustain for the role's seniority.

    A senior interview that never leaves difficulty 1 cannot prove senior
    ability — the governor and the session seed clamp to this floor.
    """
    label = (job_role or "").lower()
    for keywords, floor in _ROLE_FLOOR_RULES:
        if any(k in label for k in keywords):
            return floor
    return 1


def _recent_answer_scores(state: InterviewState, window: int = 3) -> list[float]:
    """The last ``window`` per-question evidence scores, in question order.

    Uses the evidence store (the numbers the candidate and report actually
    see) instead of the unified-evaluation dimension average, so the governor
    reacts to sustained performance rather than one noisy answer.
    """
    by_question: dict[int, float] = {}
    for ev in state.get("evidence_store") or []:
        q = int(ev.get("question_number", 0) or 0)
        s = ev.get("score")
        if q > 0 and s is not None:
            by_question[q] = float(s)
    return [by_question[q] for q in sorted(by_question)][-window:]


def _serious_contradiction_count(state: InterviewState) -> int:
    # Single source of contradiction truth (T1.2): the brain layer assembled by
    # build_contradiction_state carries the normalized list; fall back to the
    # raw runtime list only when the layer was never assembled.
    cs = state.get("contradiction_state") or {}
    contradictions = cs.get("contradictions")
    if contradictions is None:
        contradictions = state.get("contradictions") or []
    return sum(
        1 for c in contradictions
        if c.get("severity") in ("high", "medium")
    )


def _calibration_shallow(state: InterviewState) -> bool:
    """True when the calibration brain says the evidence base is too thin to
    conclude (low depth or claim-heavy proof ratio). The governor must never
    ratchet difficulty UP into credit a level the thin evidence can't justify."""
    cal = state.get("calibration_state") or {}
    if (cal.get("evidence_depth") or "") == "low":
        return True
    return float(cal.get("proof_ratio", 1.0) or 1.0) < 0.35


async def difficulty_governor(
    state: InterviewState,
    use_llm: bool = True,
) -> InterviewState:
    """Adapt difficulty from the last evaluation.

    Reads the latest unified evaluation + hypothesis confidence and produces
    a difficulty_delta in {-1, 0, +1}, clamped to the style's difficulty range.
    When ``use_llm`` is False (or the LLM fails) the deterministic fallback is
    used. The resulting 6-dimension ``difficulty_profile`` rides along in the
    state for the question generator.

    Fix 11: a composite-score clamp is applied AFTER whichever path ran, so
    strong answers can never lower difficulty and weak answers can never raise
    it — the LLM only tunes the mid-band.
    """
    current = state.get("difficulty_level", 2)
    style = state.get("interview_style") or get_style()
    diff_min, diff_max = style.get("difficulty_range", (1, MAX_SCORE))

    if use_llm:
        try:
            delta, rationale, scaffold = await _govern_with_llm(state)
        except Exception as e:
            logger.warning(f"Difficulty governor LLM failed ({e}), using deterministic fallback")
            delta, rationale, scaffold = _govern_deterministic(state)
    else:
        delta, rationale, scaffold = _govern_deterministic(state)

    # Fix 11 (D1): the window average clamps whichever path ran — the LLM only
    # tunes inside the deterministic rule's band. Above the band difficulty can
    # never drop; at/above the hold threshold (7.0) it can never be lowered;
    # below 7.0 it can never be raised.
    recent_scores = _recent_answer_scores(state)
    if recent_scores:
        window_avg = sum(recent_scores) / len(recent_scores)
        serious = _serious_contradiction_count(state)
        if window_avg > 8.3 and serious < 2:
            delta = max(delta, 1)
        elif window_avg >= 7.0:
            delta = max(delta, 0)
        elif window_avg < 7.0 and serious < 2:
            delta = min(delta, -1)

    # Role floor: a senior interview never drops below senior-level probing,
    # whatever the LLM or the window rule says. This is what keeps the demo
    # session from pinning a Senior candidate at difficulty 1 forever.
    floor = max(diff_min, role_difficulty_floor(state.get("job_role", "")))

    # T2.4 / T1.1: never ratchet difficulty UP while the calibration brain
    # still calls the evidence base shallow — a thin interview earning easy
    # points must not be graded at a level it was never pushed to. The floor
    # below still applies, only the upward move is blocked.
    if _calibration_shallow(state) and delta > 0:
        delta = 0
        rationale = "evidence base still shallow — difficulty held (no ratchet-up): " + rationale

    next_difficulty = max(floor, min(diff_max, current + delta))

    # B3: track the peak monotonicly so difficulty_reached reports what the
    # candidate was actually pushed to, even when the governor lowers the level
    # for a closing stretch.
    max_reached = max_difficulty_reached(state)

    profile = build_difficulty_profile(state, delta, rationale)
    profile["level"] = next_difficulty

    return {
        **state,
        "difficulty_level": next_difficulty,
        "max_difficulty_reached": max(max_reached, next_difficulty),
        "difficulty_delta": delta,
        "difficulty_rationale": rationale,
        "difficulty_scaffold": scaffold,
        "difficulty_profile": profile,
    }


async def _govern_with_llm(state: InterviewState) -> tuple[int, str, str]:
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    llm_service = get_llm_service()

    evaluation = state.get("unified_evaluation", {}) or {}
    score_lines = []
    for dim, data in evaluation.items():
        if isinstance(data, dict) and data.get("score") is not None:
            score_lines.append(
                f"- {dim}: score={data['score']}, confidence={data.get('confidence', 0.0)}"
            )
    score_summary = "\n".join(score_lines) or "(no scored dimensions)"

    hypothesis_target = state.get("hypothesis_target") or {}
    target_confidence = hypothesis_target.get("confidence", 0.0)
    target_status = hypothesis_target.get("status", "untested")

    current = state.get("difficulty_level", 2)
    last_answer = ""
    conv = state.get("conversation_history", [])
    for h in reversed(conv):
        if h.get("role") == "user":
            last_answer = h.get("content", "")[:600]
            break

    serious_contradictions = _serious_contradiction_count(state)
    answer_complexity = complexity_signal(last_answer)
    # D1: the governor speaks the report's language — the recent-answers
    # window average, never an opaque dimension average.
    recent_scores = _recent_answer_scores(state)
    recent_average = (sum(recent_scores) / len(recent_scores)) if recent_scores else None

    prompt = load_prompt(
        "difficulty_governor",
        "difficulty_governor.md",
        current=current,
        score_summary=score_summary,
        recent_average_score=f"{recent_average:.2f}" if recent_average is not None else "N/A",
        target_confidence=f"{target_confidence:.2f}",
        target_status=target_status,
        last_answer=last_answer or "(none yet)",
        contradiction_count=serious_contradictions,
        answer_complexity=answer_complexity,
        confidence_delta=f"{abs(float(target_confidence or 0.0) - 0.5):.2f}",
    )

    response = await llm_service.invoke(prompt=prompt, temperature=0.2, max_tokens=150, tier="cheap")
    data = _extract_json_object(response)

    delta = int(data.get("delta", 0))
    if delta not in (-1, 0, 1):
        delta = 0
    return delta, str(data.get("rationale", "")), str(data.get("scaffold", ""))


def _govern_deterministic(state: InterviewState) -> tuple[int, str, str]:
    """D1: deterministic difficulty move from a recent-answers window.

    Window rule (matches the report's own per-question scores):
        last-3 average > 8.3  -> +1 (sustained strong performance)
        last-3 average < 7.0  -> -1 (sustained weak performance)
        otherwise             ->  0 (hold)

    A single noisy answer can no longer swing difficulty — the window
    buffers it.
    """
    recent_scores = _recent_answer_scores(state)
    if not recent_scores:
        return 0, "No evidence yet, keeping difficulty steady", ""

    window_avg = sum(recent_scores) / len(recent_scores)

    if window_avg > 8.3:
        return 1, f"Recent answers averaging {window_avg:.2f} — increasing difficulty", "push on trade-offs and edge cases"
    if window_avg < 7.0:
        return -1, f"Recent answers averaging {window_avg:.2f} — scaffolding down", "ask for a concrete example and walk through the thought process"
    return 0, f"Recent answers averaging {window_avg:.2f} — keeping difficulty steady", ""
