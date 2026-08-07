"""Question Planner / Interview Strategy V5.

The planner decides which question gives the maximum intelligence information,
not "question number 5". Each turn it ranks competencies by uncertainty and
chooses one of five question modes:

    explore      — unexplained, leading hypothesis (high uncertainty)
    verify       — borderline evidence, pin down the level
    challenge    — claimed seniority needs pressure-testing (fake-depth check)
    contradict   — a direct contradiction needs resolution
    deepen       — strong-but-thin surface, push to ownership/depth
    conclude     — no remaining uncertainty worth chasing

Deterministic: consumes the uncertainty map + hypothesis/risk state and emits
``question_strategy`` + the ``planned_competency`` the engine should probe next.
"""
import logging

logger = logging.getLogger(__name__)

CONTRADICTION_ACTIONS = ("challenge", "contradict")


def _decide_mode(
    comp_id: str,
    uncertainty_entry: dict,
    contradiction_state: dict,
    hypothesis_brain: list[dict],
) -> dict:
    entry = uncertainty_entry or {}
    uncertainty = float(entry.get("uncertainty", 0.5) or 0.5)
    missing = entry.get("missing_evidence") or []
    hyp = next(
        (h for h in hypothesis_brain or [] if h.get("competency") == comp_id),
        None,
    )
    status = (hyp or {}).get("status") or "untested"

    seniority_action = (contradiction_state or {}).get("needs_challenge")
    seniority_risk = (contradiction_state or {}).get("seniority_risk", {}) or {}
    risk_level = seniority_risk.get("level") or "low"
    risk_action = seniority_risk.get("action") or "validate"

    if seniority_action or risk_action == "challenge":
        if uncertainty >= 0.4 or risk_level in ("high", "medium"):
            return "challenge"
    if status == "untested" or uncertainty >= 0.7:
        return "explore"
    if (contradiction_state or {}).get("contradictions"):
        return "contradict"
    if not missing:
        return "verify"
    if uncertainty >= 0.45:
        return "deepen"
    return "validate"


def _mode_note(mode: str) -> str:
    return {
        "explore": "high uncertainty — collect base evidence",
        "verify": "core evidence gathered — confirm the level",
        "challenge": "pressure-test claimed seniority and ownership",
        "contradict": "resolve a direct contradiction in the evidence",
        "deepen": "push to depth: ownership, tradeoffs, failure handling",
        "validate": "low uncertainty — confirm-and-conclude",
    }.get(mode, "")


def generate_question_strategy(
    *,
    uncertainty_map: dict,
    contradiction_state: dict,
    hypothesis_brain: list[dict],
    competency_summary: dict | None = None,
) -> dict:
    """Select the next competency and question mode (max-information rule)."""
    competency_summary = competency_summary or {}
    ranked = sorted(
        uncertainty_map.items(),
        key=lambda kv: (kv[1].get("uncertainty", 0.0), kv[1].get("importance", 0)),
        reverse=True,
    )

    if not ranked:
        return {
            "question_strategy": {"action": "conclude", "mode": "conclude"},
            "planned_competency": None,
            "next_question_strategy": {"action": "conclude", "mode": "conclude", "target": None},
            "rationale": "no remaining uncertainty worth pursuing",
        }

    comp_id, entry = ranked[0]
    mode = _decide_comp_mode(comp_id, entry, contradiction_state, hypothesis_brain)
    note = _mode_note(mode)
    action = "ask" if mode not in ("validate", "none") else ("validate" if mode == "validate" else "conclude")

    return {
        "question_strategy": {
            "action": action,
            "mode": mode,
            "note": note,
            "target_competency": comp_id,
            "uncertainty": entry.get("uncertainty", 0.0),
        },
        "planned_competency": comp_id if mode != "conclude" else None,
        "next_question_strategy": {
            "action": mode,
            "target": comp_id if mode != "conclude" else None,
            "reduce_uncertainty": entry.get("uncertainty", 0.0),
            "note": note,
        },
        "rationale": _rationale(mode, entry),
    }


def _decide_comp_mode(
    comp_id: str,
    entry: dict,
    contradiction_state: dict,
    hypothesis_brain: list[dict],
) -> str:
    return _decide_mode(comp_id, dict(entry or {}), contradiction_state or {}, hypothesis_brain or [])


def _rationale(mode: str, entry: dict) -> str:
    base = {
        "challenge": "claimed seniority must be proven under pressure",
        "explore": "highest uncertainty/importance — maximum information gain",
        "verify": "borderline coverage — pin the confidence",
        "contradict": "direct contradiction needs resolution",
        "deepen": "strong claim, thin proof — push to ownership and failure handling",
        "validate": "evidence satisfied — confirm and prepare conclusion",
    }.get(mode, "")
    return base + f" (uncertainty={entry.get('uncertainty', 0)})"