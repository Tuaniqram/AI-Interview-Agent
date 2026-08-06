"""V5 director — the internal decision controller.

Decides the next interview action from the reflection signals plus richer
inputs (hypothesis confidence, difficulty, unanswered hypotheses, question
budget, loop counters). Pure and deterministic so the interview's direction is
never opaque or hostage to an LLM.

Action vocabulary (four actions):
    CONTINUE         — proceed with the next target selection as normal
    PROBE            — drill deeper into the current target (counter-evidence)
    CHANGE_COMPETENCY — rotate to another competency / regenerate hypotheses
    FINISH           — end the interview

The engine commits the decision to ``brain.director`` and routes on its
``action``.
"""
from app.agents.reasoning.contradiction_engine import MIN_QUESTIONS_BEFORE_FINISH

# How many consecutive turns the same hypothesis may be the target before the
# director forces a rotation (prevents reflection loops).
MAX_CONSECUTIVE_PROBES = 3

# A belief at/above this confidence is treated as established — the director
# then prefers probing for counter-evidence over continuing to gather support.
DEEP_PROBE_CONFIRMED_FLOOR = 0.7

# Probe-mode thresholds (AURA V5 question selector).
CHALLENGE_DIFFICULTY_FLOOR = 4
VERIFY_SCORE_FLOOR = 7.5
VERIFY_CONFIDENCE_CEIL = 0.75

_SERIOUS_SEVERITIES = ("high", "medium")

DIRECTOR_ACTIONS = ("CONTINUE", "PROBE", "CHANGE_COMPETENCY", "FINISH")
PROBE_MODES = (
    "explore_new_competency",
    "deep_probe",
    "challenge_candidate",
    "verify_claim",
    "finish_competency",
)

__all__ = [
    "MAX_CONSECUTIVE_PROBES",
    "DEEP_PROBE_CONFIRMED_FLOOR",
    "CHALLENGE_DIFFICULTY_FLOOR",
    "VERIFY_SCORE_FLOOR",
    "VERIFY_CONFIDENCE_CEIL",
    "DIRECTOR_ACTIONS",
    "PROBE_MODES",
    "director_controller",
]


def _probe_mode_for(action: str, state: dict) -> str:
    """Pick the interviewer mode the next question should take (Fix 2/4).

    Maps the coarse director action onto the 5-mode selector:
        FINISH            → finish_competency
        CHANGE_COMPETENCY  → explore_new_competency (first probe of a new area)
        PROBE              → deep_probe (counter-evidence on an established belief)
        CONTINUE           → challenge_candidate when pushing a senior candidate,
                             verify_claim when the last answer scored high but the
                             belief is still open, else explore_new_competency.
    """
    if action == "FINISH":
        return "finish_competency"
    if action == "CHANGE_COMPETENCY":
        return "explore_new_competency"
    if action == "PROBE":
        return "deep_probe"

    difficulty = int(state.get("difficulty_level", 1) or 1)
    target = state.get("hypothesis_target") or {}
    status = target.get("status", "untested")
    confidence = float(target.get("confidence", 0.0) or 0.0)
    score = state.get("evaluation_score")
    score = float(score) if score is not None else 0.0

    if status in ("testing", "confirmed") and difficulty >= CHALLENGE_DIFFICULTY_FLOOR:
        return "challenge_candidate"
    if status == "testing" and score >= VERIFY_SCORE_FLOOR and confidence < VERIFY_CONFIDENCE_CEIL:
        return "verify_claim"
    return "explore_new_competency"


def director_controller(state: dict) -> dict:
    """Decide the next interview action from the current reasoning state.

    Returns ``{"action": ..., "reason": ..., "probe_mode": ..., "target_id": ...}``
    where ``probe_mode`` is the 5-mode question selector (Fix 2) and
    ``target_id`` is set when the decision is scoped to a specific hypothesis.
    """
    action, reason, target_id = _director_decision(state)
    decision = {"action": action, "reason": reason}
    if target_id:
        decision["target_id"] = target_id
    decision["probe_mode"] = _probe_mode_for(action, state)
    return decision


def _director_decision(state: dict) -> tuple[str, str, str]:
    reflection_action = state.get("reflection_action", "probe")
    evidence_sufficiency = state.get("evidence_sufficiency") or {}
    contradictions = state.get("contradictions") or []
    question_number = int(state.get("question_number", 0) or 0)
    max_questions = int(state.get("max_questions", 14) or 14)
    target = state.get("hypothesis_target") or {}
    target_id = target.get("id", "")
    consecutive_probes = int(state.get("consecutive_probes", 0) or 0)
    last_target_id = state.get("last_hypothesis_target_id", "")

    if reflection_action == "finish" or evidence_sufficiency.get("is_sufficient"):
        # Fix 11: never finish before the minimum question count — a hiring
        # decision needs an evidence base, so keep probing even when the
        # reflection signals finish. Rotations still proceed normally.
        if question_number >= MIN_QUESTIONS_BEFORE_FINISH:
            return (
                "FINISH",
                "evidence sufficiency met or reflection signaled finish",
                target_id,
            )
        return (
            "CONTINUE",
            f"below minimum question count ({MIN_QUESTIONS_BEFORE_FINISH}) — keep probing",
            target_id,
        )

    if question_number >= max_questions:
        return (
            "FINISH",
            f"question budget exhausted (max {max_questions})",
            target_id,
        )

    if reflection_action == "change_competency":
        return (
            "CHANGE_COMPETENCY",
            "reflection signaled a competency rotation",
            target_id,
        )

    serious = [
        c for c in contradictions
        if c.get("severity") in _SERIOUS_SEVERITIES
    ]
    if len(serious) >= 2:
        return (
            "CHANGE_COMPETENCY",
            f"{len(serious)} serious contradictions found",
            target_id,
        )

    # Loop guard: the same hypothesis probed without movement is a rotation
    # trigger, not a reason to keep asking.
    if target_id and target_id == last_target_id and consecutive_probes >= MAX_CONSECUTIVE_PROBES:
        return (
            "CHANGE_COMPETENCY",
            (
                f"target {target_id} probed {consecutive_probes} consecutive turns "
                "without a belief shift"
            ),
            target_id,
        )

    # Probe for counter-evidence once a belief looks established.
    status = target.get("status", "untested")
    confidence = float(target.get("confidence", 0.0) or 0.0)
    if status in ("confirmed", "testing") and confidence >= DEEP_PROBE_CONFIRMED_FLOOR:
        return (
            "PROBE",
            f"{status} belief at {confidence:.2f} — probe for counter-evidence",
            target_id,
        )

    return "CONTINUE", "proceed with next target selection", target_id
