"""AURA Brain V5 — multi-layer intelligence package.

Layers (each has one responsibility, mirroring a senior interviewer):

    company_brain        — what kind of engineer succeeds here
    role_brain           — what the role actually requires (role KB + adaptation)
    competency_graph     — competencies as a graph, not a list
    hypotheses           — beliefs + confidence + missing evidence
    evidence_graph       — typed claim→evidence→competency edges
    uncertainty_map      — per-competency uncertainty for planning
    question_strategy    — the next question mode (explore/verify/challenge/
                           contradict/deepen/conclude)
    difficulty_state     — role-floor-aware difficulty position
    contradiction_state  — fake-seniority / evidence-conflict risk
    calibration_state    — calibrated quality (never bare score > 8 = hire)
    decision_state       — final deterministic decision + risks
    candidate_memory     — long-term candidate learning record

Deterministic by design: the reasoning layers never add LLM calls — they
operate on the evidence, hypotheses and company/role facts already produced.
"""
from app.brain.assembler import assemble_aura_brain  # noqa: E402

__all__ = ["assemble_aura_brain"]