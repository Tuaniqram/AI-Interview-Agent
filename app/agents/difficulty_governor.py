import json
import logging

from app.graph.interview_state import InterviewState
from app.config.interview_styles import get_style

logger = logging.getLogger(__name__)

MIN_SCORE = 1
MAX_SCORE = 4


async def difficulty_governor(state: InterviewState) -> InterviewState:
    """Adapt difficulty from the last evaluation.

    Reads the latest unified evaluation + hypothesis confidence and produces
    a difficulty_delta in {-1, 0, +1}, clamped to the style's difficulty range.
    """
    current = state.get("difficulty_level", 2)
    style = state.get("interview_style") or get_style()
    diff_min, diff_max = style.get("difficulty_range", (1, MAX_SCORE))

    try:
        delta, rationale, scaffold = await _govern_with_llm(state)
    except Exception as e:
        logger.warning(f"Difficulty governor LLM failed ({e}), using deterministic fallback")
        delta, rationale, scaffold = _govern_deterministic(state)

    next_difficulty = max(diff_min, min(diff_max, current + delta))

    return {
        **state,
        "difficulty_level": next_difficulty,
        "difficulty_delta": delta,
        "difficulty_rationale": rationale,
        "difficulty_scaffold": scaffold,
    }


async def _govern_with_llm(state: InterviewState) -> tuple[int, str, str]:
    from app.services.llm_service import get_llm_service

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

    prompt = f"""You are the difficulty governor for an adaptive interview conductor.

Current difficulty: {current} (1=easy, 2=medium, 3=hard, 4=expert)
Latest evaluation scores:
{score_summary}

Target hypothesis confidence: {target_confidence}, status: {target_status}
Candidate's last answer: {last_answer or '(none yet)'}

Decide the difficulty change for the NEXT question:
- +1: candidate is clearly strong (high scores, high confidence, specific answers) — go harder
- 0: keep steady (mixed or early interview)
- -1: candidate struggled (low scores, vague answers) — scaffold down

Output ONLY valid JSON:
{{
  "delta": -1 | 0 | 1,
  "rationale": "<one sentence>",
  "scaffold": "<brief instruction for the interviewer, e.g. 'ask for a concrete example', or empty string>"
}}"""

    response = await llm_service.invoke(prompt=prompt, temperature=0.2, max_tokens=150)
    data = json.loads(response.strip().lstrip("```json").rstrip("```").strip())

    delta = int(data.get("delta", 0))
    if delta not in (-1, 0, 1):
        delta = 0
    return delta, str(data.get("rationale", "")), str(data.get("scaffold", ""))


def _govern_deterministic(state: InterviewState) -> tuple[int, str, str]:
    evaluation = state.get("unified_evaluation", {}) or {}
    scores = [
        data["score"]
        for data in evaluation.values()
        if isinstance(data, dict) and data.get("score") is not None
    ]

    hypothesis_target = state.get("hypothesis_target") or {}
    confidence = float(hypothesis_target.get("confidence", 0.0) or 0.0)

    if not scores:
        return 0, "No evaluation yet, keeping difficulty steady", ""

    avg = sum(scores) / len(scores)

    if avg >= 7.5 and confidence >= 0.6:
        return 1, "Strong performance with high confidence — increasing difficulty", "push on trade-offs and edge cases"
    if avg >= 7.5:
        return 1, "Strong performance — increasing difficulty", ""
    if avg <= 4.5:
        return -1, "Weak performance — scaffolding down", "ask for a concrete example and walk through the thought process"
    return 0, "Mixed performance — keeping difficulty steady", ""
