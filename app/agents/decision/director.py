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
# How many consecutive turns the same hypothesis may be the target before the
# director forces a rotation (prevents reflection loops).
MAX_CONSECUTIVE_PROBES = 3

# A belief at/above this confidence is treated as established — the director
# then prefers probing for counter-evidence over continuing to gather support.
DEEP_PROBE_CONFIRMED_FLOOR = 0.7

_SERIOUS_SEVERITIES = ("high", "medium")

DIRECTOR_ACTIONS = ("CONTINUE", "PROBE", "CHANGE_COMPETENCY", "FINISH")

__all__ = [
    "MAX_CONSECUTIVE_PROBES",
    "DEEP_PROBE_CONFIRMED_FLOOR",
    "DIRECTOR_ACTIONS",
    "director_controller",
]


def director_controller(state: dict) -> dict:
    """Decide the next interview action from the current reasoning state.

    Returns ``{"action": ..., "reason": ..., "target_id": ...}`` where
    ``target_id`` is set when the decision is scoped to a specific hypothesis.
    """
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
        return {
            "action": "FINISH",
            "reason": "evidence sufficiency met or reflection signaled finish",
        }

    if question_number >= max_questions:
        return {
            "action": "FINISH",
            "reason": f"question budget exhausted (max {max_questions})",
        }

    if reflection_action == "change_competency":
        return {
            "action": "CHANGE_COMPETENCY",
            "reason": "reflection signaled a competency rotation",
        }

    serious = [
        c for c in contradictions
        if c.get("severity") in _SERIOUS_SEVERITIES
    ]
    if len(serious) >= 2:
        return {
            "action": "CHANGE_COMPETENCY",
            "reason": f"{len(serious)} serious contradictions found",
        }

    # Loop guard: the same hypothesis probed without movement is a rotation
    # trigger, not a reason to keep asking.
    if target_id and target_id == last_target_id and consecutive_probes >= MAX_CONSECUTIVE_PROBES:
        return {
            "action": "CHANGE_COMPETENCY",
            "reason": (
                f"target {target_id} probed {consecutive_probes} consecutive turns "
                "without a belief shift"
            ),
        }

    # Probe for counter-evidence once a belief looks established.
    status = target.get("status", "untested")
    confidence = float(target.get("confidence", 0.0) or 0.0)
    if status in ("confirmed", "testing") and confidence >= DEEP_PROBE_CONFIRMED_FLOOR:
        return {
            "action": "PROBE",
            "reason": f"{status} belief at {confidence:.2f} — probe for counter-evidence",
            "target_id": target_id,
        }

    return {
        "action": "CONTINUE",
        "reason": "proceed with next target selection",
    }
