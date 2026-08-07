"""AURA Brain V5 — the assembler.

Builds the full multi-layer brain object from the intelligence bundle and the
runtime reasoning state. Every layer is deterministic — no new LLM calls (the
LLM traces already produced the bundle pieces).

Output shape (matches the requirement):

    {
      company_brain: {...},
      role_brain: {...},
      competency_graph: {...},
      hypotheses: [...],
      evidence_graph: {...},
      uncertainty_map: {...},
      question_strategy: {...},
      difficulty_state: {...},
      contradiction_state: {...},
      calibration_state: {...},
      decision_state: {...}
    }
"""
import logging

from app.brain.calibration import build_calibration_state
from app.brain.candidate_memory import (
    build_candidate_memory,
    memory_into_candidate_brain,
)
from app.brain.company_brain import build_v5_company_brain
from app.brain.contradiction_detector import build_contradiction_state
from app.brain.decision_engine import build_decision_state
from app.brain.evidence_reasoner import (
    evidence_cursor,
    evidence_summary_stats,
    evidence_to_graph,
)
from app.brain.hypothesis_engine import (
    build_hypothesis_brain,
    uncertainty_map,
)
from app.brain.question_planner import generate_question_strategy
from app.brain.role_brain import build_role_brain
from app.data.competency_graph import taxonomy_to_graph

logger = logging.getLogger(__name__)


def assemble_aura_brain(
    *,
    job_role: str,
    company_brain: dict | None = None,
    taxonomy: list[dict] | None = None,
    required_competencies: list[str] | None = None,
    role_context: dict | None = None,
    candidate_brain: dict | None = None,
    candidate_assessment: dict | None = None,
    candidate_id: str = "",
    hypotheses: list[dict] | None = None,
    evidence_store: list[dict] | None = None,
    competency_summary: dict | None = None,
    contradictions: list | None = None,
    difficulty_reached: int | None = None,
    role_floor: int | None = None,
    hiring_recommendation: dict | None = None,
    hiring_decision: dict | None = None,
    prior_candidate_memory: dict | None = None,
) -> dict:
    """Assemble the complete V5 brain dict (used at build, start and report)."""
    taxonomy = list(taxonomy or [])
    required_ids = list(required_competencies or [])
    hypotheses = list(hypotheses or [])
    evidence_store = list(evidence_store or [])
    competency_summary = dict(competency_summary or {})
    contradictions = list(contradictions or [])

    v5_company_brain = build_v5_company_brain(company_brain or {}, job_role)

    role_brain = build_role_brain(
        job_role=job_role,
        taxonomy=taxonomy,
        required_competencies=required_ids,
        role_context=role_context,
        company_brain=company_brain,
    )

    graph = taxonomy_to_graph(taxonomy, required_ids)
    hypothesis_brain = build_hypothesis_brain(
        hypotheses,
        evidence_store,
        competency_summary,
        role_brain=role_brain,
        competency_graph=graph,
    )

    uncer_map = uncertainty_map(hypothesis_brain, competency_summary, taxonomy)

    contradiction_state = build_contradiction_state(
        contradictions,
        evidence_store,
        role_brain,
    )

    evidence_stats = evidence_summary_stats(evidence_store)
    typed_graph = evidence_to_graph(
        evidence_store,
        competency_graph=graph,
        role_brain=role_brain,
    )

    question_strategy = generate_question_strategy(
        uncertainty_map=uncer_map,
        contradiction_state=contradiction_state,
        hypothesis_brain=hypothesis_brain,
        competency_summary=competency_summary,
    )

    difficulty_state = {
        "difficulty_reached": difficulty_reached or 1,
        "role_floor": role_floor,
        "floor_satisfied": (difficulty_reached or 1) >= (role_floor or 1),
        "evidence_depth": evidence_stats.get("total", 0),
    }

    calibration_state = build_calibration_state(
        hiring_recommendation=hiring_recommendation or {},
        difficulty_reached=difficulty_reached or 1,
        role_floor=role_floor,
        total_evidence=evidence_stats.get("total", 0),
        proof_ratio=evidence_stats.get("proof_ratio", 0.0),
        resolved_ratio=_resolved_ratio(hypotheses),
        serious_contradictions=sum(
            1
            for c in contradiction_state.get("contradictions", [])
            if c.get("severity") in ("high", "medium")
        ),
    )

    decision_state = build_decision_state(
        hiring_decision=hiring_decision or {},
        hiring_recommendation=hiring_recommendation or {},
        calibration_state=calibration_state,
    )

    memory = build_candidate_memory(
        candidate_id=candidate_id,
        candidate_brain=candidate_brain,
        candidate_assessment=candidate_assessment,
        prior_memory=prior_candidate_memory,
    )

    return {
        "company_brain": v5_company_brain,
        "role_brain": role_brain,
        "competency_graph": graph,
        "hypotheses": hypothesis_brain,
        "evidence_graph": typed_graph,
        "uncertainty_map": uncer_map,
        "question_strategy": question_strategy,
        "difficulty_state": difficulty_state,
        "contradiction_state": contradiction_state,
        "calibration_state": calibration_state,
        "decision_state": decision_state,
        "candidate_memory": memory,
    }


def _resolved_ratio(hypotheses: list[dict]) -> float:
    settled = [h for h in hypotheses if h.get("status") in ("confirmed", "refuted")]
    total = len(hypotheses)
    return round(len(settled) / total, 4) if total else 0.0


_CONCLUSIVE_VERDICTS = {"strong_hire", "hire", "weak", "reject"}


def _turn_is_conclusive(aura: dict) -> bool:
    """T2.6: was this turn a \"convincing close\" candidate?

    Deterministic per-turn verdict signal from the decision + calibration
    layers: a decisive verdict with high confidence, deep-enough evidence and
    no risk flags. The director only lets a streak of these close the
    interview early — never a single strong turn.
    """
    decision = aura.get("decision_state") or {}
    calibration = aura.get("calibration_state") or {}
    if decision.get("decision") not in _CONCLUSIVE_VERDICTS:
        return False
    if float(decision.get("confidence") or 0.0) < 0.7:
        return False
    if (calibration.get("evidence_depth") or "") == "low":
        return False
    if calibration.get("proof_ratio", 1.0) < 0.35:
        return False
    if decision.get("risk_flags"):
        return False
    return True


def build_aura_from_state(state: dict) -> dict:
    """Assemble the V5 brain from a runtime state dict (engine path)."""
    from app.agents.planning.difficulty_engine import role_difficulty_floor

    job_role = state.get("job_role", "")
    return assemble_aura_brain(
        job_role=job_role,
        company_brain=state.get("company_brain"),
        taxonomy=state.get("competency_taxonomy"),
        required_competencies=state.get("required_competencies"),
        role_context=state.get("role_context"),
        candidate_brain=state.get("candidate_brain"),
        candidate_assessment=state.get("candidate_assessment"),
        candidate_id=state.get("candidate_id", ""),
        hypotheses=state.get("hypotheses"),
        evidence_store=state.get("evidence_store"),
        competency_summary=state.get("competency_summary"),
        contradictions=state.get("contradictions"),
        difficulty_reached=int(state.get("difficulty_level") or 1),
        role_floor=role_difficulty_floor(job_role),
        hiring_recommendation=state.get("hiring_recommendation"),
        hiring_decision=state.get("hiring_decision"),
        prior_candidate_memory=(state.get("candidate_brain") or {}).get("candidate_memory"),
    )


_LAYER_NAMES = (
    "company_brain",
    "role_brain",
    "competency_graph",
    "hypotheses",
    "evidence_graph",
    "uncertainty_map",
    "question_strategy",
    "difficulty_state",
    "contradiction_state",
    "calibration_state",
    "decision_state",
    "candidate_memory",
)


def build_brain_utilization(aura: dict, state: dict) -> dict:
    """Which of the 12 brain layers carried live weight on the last turn.

    Deterministic observability report: every layer gets a status
    (``drives_turn`` / ``feeds_decision`` / ``idle``) plus a one-line note
    saying what signal the layer actually contributed right now, so a caller
    can see at a glance whether the brain is steering the interview or just
    being serialized.
    """
    def _status(layer: str) -> tuple[str, str]:
        if layer == "company_brain":
            cb = aura.get("company_brain") or {}
            active = bool(cb.get("company_vision") or cb.get("technical_stack"))
            return ("drives_turn", "grounds EXPLORER questions in company context") if active else ("idle", "no company intelligence")
        if layer == "role_brain":
            rb = aura.get("role_brain") or {}
            req = rb.get("required_competencies") or []
            floor = rb.get("difficulty_floor") or aura.get("difficulty_state") or {}
            floor_v = floor.get("role_floor") if isinstance(floor, dict) else None
            return ("drives_turn", f"{len(req)} required competencies, floor={floor_v}") if req else ("idle", "no role requirements")
        if layer == "competency_graph":
            nodes = (aura.get("competency_graph") or {}).get("nodes") or {}
            return ("feeds_decision", f"{len(nodes)} competency nodes") if nodes else ("idle", "empty graph")
        if layer == "hypotheses":
            hyps = aura.get("hypotheses") or []
            settled = sum(1 for h in hyps if h.get("status") in ("confirmed", "refuted"))
            return ("drives_turn", f"{len(hyps)} hypotheses, {settled} settled") if hyps else ("idle", "no hypotheses")
        if layer == "evidence_graph":
            edges = (aura.get("evidence_graph") or {}).get("edges") or []
            typed = [e for e in edges if e.get("relation") in ("supports", "contradicts")]
            contrad = sum(1 for e in typed if e.get("relation") == "contradicts")
            return ("drives_turn", f"{len(typed)} typed edges, {contrad} contradicts") if typed else ("idle", "no typed evidence yet")
        if layer == "uncertainty_map":
            uncer = aura.get("uncertainty_map") or {}
            if isinstance(uncer, dict):
                vals = [u for u in uncer.values() if isinstance(u, (int, float)) and u > 0]
                return ("drives_turn", f"{len(vals)} competencies with uncertainty") if vals else ("idle", "no open uncertainty")
            return ("idle", "no uncertainty data")
        if layer == "question_strategy":
            strat = aura.get("question_strategy") or {}
            mode = strat.get("mode") or strat.get("question_strategy", {}).get("mode") or ""
            return ("drives_turn", f"mode={mode}") if mode else ("idle", "no strategy mode")
        if layer == "difficulty_state":
            ds = aura.get("difficulty_state") or {}
            floor_ok = ds.get("floor_satisfied", True)
            return ("drives_turn", f"reached={ds.get('difficulty_reached')} floor_ok={floor_ok}") if not floor_ok else ("feeds_decision", f"reached={ds.get('difficulty_reached')}")
        if layer == "contradiction_state":
            cs = aura.get("contradiction_state") or {}
            n = len(cs.get("contradictions") or [])
            challenge = cs.get("needs_challenge", False)
            return ("drives_turn", f"{n} contradictions, challenge={challenge}") if (n or challenge) else ("idle", "no contradictions")
        if layer == "calibration_state":
            cal = aura.get("calibration_state") or {}
            depth = cal.get("evidence_depth", "")
            proof = cal.get("proof_ratio", 1.0)
            active = depth == "low" or float(proof or 0.0) < 0.35
            return ("drives_turn", f"depth={depth} proof={proof}") if active else ("feeds_decision", f"depth={depth} proof={proof}")
        if layer == "decision_state":
            dec = aura.get("decision_state") or {}
            verdict = dec.get("decision") or ""
            conclusive = bool(dec.get("confidence") or 0) >= 0.8 and not dec.get("risk_flags")
            return ("drives_turn", f"verdict={verdict} conclusive={conclusive}") if conclusive else ("feeds_decision", f"verdict={verdict}")
        if layer == "candidate_memory":
            mem = aura.get("candidate_memory") or {}
            learned = mem.get("learned_strengths") or []
            return ("drives_turn", f"{len(learned)} learned strengths") if learned else ("idle", "no prior memory")

    layers = {}
    for name in _LAYER_NAMES:
        status, note = _status(name)
        layers[name] = {"status": status, "note": note}

    # Which layers actually fed the last director decision (best-effort: match
    # the decision reason text against the layer signals it references).
    director = state.get("director") or {}
    influenced = []
    reason = str(director.get("reason") or "").lower()
    action = director.get("action") or ""
    if action in ("FINISH", "CHANGE_COMPETENCY") or "sufficien" in reason or "gap" in reason or "coverage" in reason:
        influenced.append("calibration_state")
    if "contradict" in reason or "challenge" in reason or "seniority" in reason:
        influenced.append("contradiction_state")
    if "difficulty" in reason or "floor" in reason or "budget" in reason:
        influenced.append("difficulty_state")
    if "prob" in reason or "target" in reason or "belief" in reason or "counter-evidence" in reason:
        influenced.append("hypotheses")
        influenced.append("evidence_graph")
    if "competency" in reason or "rotate" in reason:
        influenced.append("question_strategy")
        influenced.append("uncertainty_map")
    if influenced:
        influenced = list(dict.fromkeys(influenced))

    return {
        "question_number": int(state.get("question_number", 0) or 0),
        "layers": layers,
        "influenced_last_decision": influenced,
    }


def refresh_brain_layers(brain) -> "InterviewBrain":
    """Re-run the live brain layers (uncertainty, strategy, contradiction)
    over a runtime brain after every answer — the planner always sees the
    freshest evidence state."""
    try:
        aura = build_aura_from_state(brain.to_dict())
        brain.aura_brain = aura
        brain.uncertainty_map = aura["uncertainty_map"]
        brain.question_strategy = aura["question_strategy"]
        brain.contradiction_state = aura["contradiction_state"]
        brain.calibration_state = aura["calibration_state"]
        brain.competency_graph = aura["competency_graph"]
        brain.role_brain = aura["role_brain"]
        brain.difficulty_state = aura["difficulty_state"]
        brain.decision_state = aura["decision_state"]
        brain.candidate_memory = aura["candidate_memory"]
        brain.evidence_cursor = evidence_cursor(aura["evidence_graph"])
        prev_streak = getattr(brain, "conclusive_turns", 0) or 0
        brain.conclusive_turns = prev_streak + 1 if _turn_is_conclusive(aura) else 0
        brain.brain_utilization = build_brain_utilization(aura, brain.to_dict())
    except Exception as exc:  # noqa: BLE001 - live brain refresh is best-effort
        logger.warning(f"Live brain layer refresh failed (non-fatal): {exc}")
    return brain