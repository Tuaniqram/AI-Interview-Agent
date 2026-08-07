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
from app.agents.reasoning.contradiction_engine import (
    MIN_QUESTIONS_BEFORE_FINISH,
    _required_gaps_ok,
)

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

    AURA V5 overrides: a live calibration gate blocks topic rotation (challenge
    the current target instead), a typed-graph contradicts edge forces
    challenge_candidate over generic probing, and challenge requires the
    role's difficulty floor to be satisfied first.
    """
    if action == "FINISH":
        return "finish_competency"

    # T1.2: deterministic seniority-risk flag wins over every mode.
    _, needs_challenge = _contradiction_signal(state)
    if needs_challenge:
        return "challenge_candidate"

    if action == "CHANGE_COMPETENCY":
        # T1.1: evidence too shallow to conclude — don't rotate topics, stay
        # and pressure-test the current claim instead.
        if _calibration_gate(state):
            return "challenge_candidate"
        return "explore_new_competency"
    if action == "PROBE":
        # T1.3: typed evidence graph pin — the target competency has a
        # contradicts edge, so re-verify instead of generic deep probing.
        if _cursor_marks_target(state, "contradicted"):
            return "challenge_candidate"
        return "deep_probe"

    difficulty = int(state.get("difficulty_level", 1) or 1)
    target = state.get("hypothesis_target") or {}
    status = target.get("status", "untested")
    confidence = float(target.get("confidence", 0.0) or 0.0)
    score = state.get("evaluation_score")
    score = float(score) if score is not None else 0.0

    # T2.4: difficulty floor not satisfied yet — no challenge mode, the
    # candidate has not been stress-tested at the role's level (probe instead).
    floor_ok = bool((state.get("difficulty_state") or {}).get("floor_satisfied", True))
    if status in ("testing", "confirmed") and difficulty >= CHALLENGE_DIFFICULTY_FLOOR and floor_ok:
        return "challenge_candidate"
    if _cursor_marks_target(state, "demonstrated") and not floor_ok:
        return "deep_probe"
    if status == "testing" and score >= VERIFY_SCORE_FLOOR and confidence < VERIFY_CONFIDENCE_CEIL:
        return "verify_claim"
    return "explore_new_competency"


def _cursor_marks_target(state: dict, kind: str) -> bool:
    """T1.3: does the typed evidence-graph cursor flag the current target's
    competency (``contradicted`` / ``demonstrated`` / ``claimed``)?"""
    target = state.get("hypothesis_target") or {}
    competency = target.get("competency", "")
    if not competency:
        return False
    cursor = state.get("evidence_cursor") or {}
    flagged = cursor.get(kind) or []
    return competency in flagged


def _contradiction_signal(state: dict) -> tuple[list[dict], bool]:
    """Single source of contradiction truth: the V5 ``contradiction_state``
    brain layer (assembled deterministically by ``build_contradiction_state``).

    Returns ``(serious_contradictions, needs_challenge)`` where ``needs_challenge``
    is the deterministic seniority-risk flag: a candidate who CLAIMS ownership
    while proof stays thin must be challenged, never silently accepted.
    """
    cs = state.get("contradiction_state") or {}
    if (cs.get("contradictions") is not None or cs.get("needs_challenge") is not None):
        serious = [
            c for c in (cs.get("contradictions") or [])
            if c.get("severity") in _SERIOUS_SEVERITIES
        ]
        return serious, bool(cs.get("needs_challenge"))
    # Fallback to the raw runtime list when the brain layer was not assembled.
    return (
        [c for c in (state.get("contradictions") or []) if c.get("severity") in _SERIOUS_SEVERITIES],
        False,
    )


def _calibration_gate(state: dict) -> str:
    """Live calibration gate: never let a shallow interview conclude.

    Returns a blocking reason when the evidence base is too thin to be
    conclusive (low evidence depth or claim-heavy proof ratio) — the director
    must keep probing rather than allow a FINISH.
    """
    cal = state.get("calibration_state") or {}
    depth = cal.get("evidence_depth", "")
    proof = cal.get("proof_ratio", 1.0)
    if depth == "low":
        return f"calibration gate: evidence depth low ({depth})"
    if float(proof or 0.0) < 0.35:
        return f"calibration gate: proof ratio {float(proof or 0.0):.2f} < 0.35"
    return ""


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
    question_number = int(state.get("question_number", 0) or 0)
    max_questions = int(state.get("max_questions", 14) or 14)
    target = state.get("hypothesis_target") or {}
    target_id = target.get("id", "")
    consecutive_probes = int(state.get("consecutive_probes", 0) or 0)
    last_target_id = state.get("last_hypothesis_target_id", "")

    if question_number >= max_questions:
        return (
            "FINISH",
            f"question budget exhausted (max {max_questions})",
            target_id,
        )

    # AURA V5: the live calibration gate — evidence too shallow to decide means
    # FINISH is never allowed, whatever the reflection signals. Fix 11
    # (min-question count) and the required-gaps check still apply on top.
    gate_reason = _calibration_gate(state)
    if reflection_action == "finish" or evidence_sufficiency.get("is_sufficient"):
        if gate_reason:
            return (
                "CONTINUE",
                f"{gate_reason} — keep probing before concluding",
                target_id,
            )
        # Fix 11: never finish before the minimum question count — a hiring
        # decision needs an evidence base, so keep probing even when the
        # reflection signals finish. Rotations still proceed normally.
        # P2: "sufficient" coverage is not enough — every required competency
        # must actually have its evidence (mirrors decide_next_action's gate).
        if question_number >= MIN_QUESTIONS_BEFORE_FINISH:
            if _required_gaps_ok(
                state.get("competency_summary") or {},
                state.get("required_competencies") or [],
                state.get("hypotheses") or [],
            ):
                return (
                    "FINISH",
                    "evidence sufficiency met or reflection signaled finish",
                    target_id,
                )
            return (
                "CONTINUE",
                "coverage sufficient but required competencies still have "
                "evidence gaps — keep probing",
                target_id,
            )
        return (
            "CONTINUE",
            f"below minimum question count ({MIN_QUESTIONS_BEFORE_FINISH}) — keep probing",
            target_id,
        )

    if reflection_action == "change_competency":
        return (
            "CHANGE_COMPETENCY",
            "reflection signaled a competency rotation",
            target_id,
        )

    # T2.6: live decision loop-close — N decisive turns in a row (with the
    # replay of the min-question count and the required-gaps gate) means the
    # evidence has been conclusive for a while; close early instead of burning
    # the budget re-asking the settled story.
    conclusive_streak = int(state.get("conclusive_turns", 0) or 0)
    if (
        conclusive_streak >= 2
        and not gate_reason
        and question_number >= MIN_QUESTIONS_BEFORE_FINISH
        and _required_gaps_ok(
            state.get("competency_summary") or {},
            state.get("required_competencies") or [],
            state.get("hypotheses") or [],
        )
    ):
        return (
            "FINISH",
            f"{conclusive_streak} consecutive decisive calibration turns — closing early",
            target_id,
        )

    # AURA V5: a deterministic seniority-risk challenge overrules rotation —
    # the candidate claimed architecture ownership with evidence too thin to
    # believe it, so the next turn must CHALLENGE, not move on.
    serious, needs_challenge = _contradiction_signal(state)
    if needs_challenge and not gate_reason:
        return (
            "PROBE",
            "seniority signal: claimed ownership lacks proof — challenge it",
            target_id,
        )
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
