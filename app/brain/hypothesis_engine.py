"""Hypothesis Engine V5 — what do we believe, and what is missing?

Wraps the runtime hypotheses (already Bayesian-updated in
``app.agents.reasoning.hypothesis_engine``) into the V5 hypothesis brain: each
hypothesis tracks its prior/posterior confidence, the evidence collected, the
EVIDENCE STILL MISSING (the crux — "not only score the candidate"), and the
uncertainty it contributes.
"""
import logging

from app.data.competency_graph import competency_children

logger = logging.getLogger(__name__)


def _connected_dimensions(competency_ids: list[str]) -> list[str]:
    out: list[str] = []
    for comp in competency_ids:
        out.append(comp)
        out.extend(competency_children(comp) or [])
    return out


def collect_evidence_for_hypothesis(hyp: dict, evidence_store: list[dict]) -> list[dict]:
    comp = hyp.get("competency")
    relevant = [ev for ev in evidence_store if ev.get("competency") == comp]
    dimension = hyp.get("dimension") or ""
    if dimension:
        relevant += [ev for ev in evidence_store if ev.get("dimension") == dimension]
    seen: dict[str, dict] = {}
    for ev in relevant:
        seen[ev.get("id") or id(ev)] = ev
    return list(seen.values())


def missing_evidence_for(
    hypothesis: dict,
    collected: list[dict],
    competency_graph: dict | None = None,
) -> list[str]:
    """The capabilities a hypothesis still lacks proof for.

    Runs the hypothesis's competency (and its knowledge-children) through the
    sub-capabilities the evidence must demonstrate. Anything past ~5 collected
    records is "enough"; the remainder is the missing-evidence list.
    """
    comp = hypothesis.get("competency") or ""
    if not comp:
        return []
    graph = competency_graph or {}
    children = [
        n.get("id")
        for n in (graph.get("nodes") or {}).values()
        if n.get("type") == "skill"
        and (n.get("id") in (competency_children(comp) or []))
    ]
    dem = children or competency_children(comp) or ["depth"]
    required_max = int(
        hypothesis.get("required_evidence") or 3
    ) * 2
    if len(collected) >= required_max:
        return []
    covered = " ".join((ev.get("evidence_text") or "").lower() for ev in collected)
    missing = [d for d in dem if d.replace("_", " ") not in covered]
    max_missing = max(1, required_max - len(collected))
    return missing[:min(max_missing, len(missing) or 1)]


def hypothesis_uncertainty(
    hypothesis: dict,
    importance: int,
    evidence_count_competency: int,
) -> float:
    """0..1 uncertainty of a hypothesis.

    Uncertainty = importance-weighted doubt: never-tested hypotheses and
    high-importance competencies are the most volatile. Evidence collected
    reduces uncertainty; a settled status floors it near zero (a
    confirmed/refuted hypothesis is no longer uncertain).
    """
    status = hypothesis.get("status") or "untested"
    if status in ("confirmed", "refuted"):
        return 0.1
    prior = float(hypothesis.get("confidence") or hypothesis.get("probability") or 0.5)
    if status == "untested":
        base = 1.0 if prior < 0.5 else 0.85
    else:
        base = 1.0 - prior
    base *= (importance / 10.0 if importance else 0.5)
    if evidence_count_competency > 0:
        base *= max(0.35, 1.0 - 0.12 * evidence_count_competency)
    return round(max(0.05, min(1.0, base)), 4)


def build_hypothesis_brain(
    hypotheses: list[dict],
    evidence_store: list[dict],
    competency_summary: dict,
    role_brain: dict | None = None,
    competency_graph: dict | None = None,
) -> list[dict]:
    """Expand each runtime hypothesis into the V5 hypothesis record."""
    importance_by_comp: dict[str, int] = {}
    for comp in (role_brain or {}).get("critical_competencies") or []:
        importance_by_comp[comp["id"]] = int(comp.get("importance") or 5)

    out = []
    for h in hypotheses or []:
        comp = h.get("competency") or ""
        collected = collect_evidence_for_hypothesis(h, evidence_store or [])
        importance = importance_by_comp.get(comp, 5)
        evidence_count_competency = int(
            (competency_summary or {}).get(comp, {}).get("evidence_count", 0) or 0
        )
        out.append(
            {
                **h,
                "confidence": round(float(h.get("confidence") or h.get("probability") or 0.5), 4),
                "collected_evidence": [ev.get("id", "") for ev in collected],
                "collected_count": len(collected),
                "required_evidence": int(h.get("required_evidence") or 3),
                "missing_evidence": missing_evidence_for(h, collected, competency_graph),
                "importance": importance,
                "uncertainty": hypothesis_uncertainty(
                    h, importance, evidence_count_competency
                ),
            }
        )
    return out


def uncertainty_map(
    hypothesis_brain: list[dict],
    competency_summary: dict,
    taxonomy: list[dict] | None = None,
) -> dict[str, dict]:
    """Per-competency uncertainty for the planner (max of its hypotheses)."""
    summary = competency_summary or {}
    out: dict[str, dict] = {}
    for h in hypothesis_brain:
        comp = h.get("competency") or ""
        summary_comp = summary.get(comp) or {}
        gap_component = float(summary_comp.get("gap", 0.0) or 0.0) * 0.6
        competency_uncertainty = round(
            max(
                gap_component,
                h.get("uncertainty", 0.5),
            ),
            4,
        )
        existing = out.get(comp, {})
        if competency_uncertainty >= existing.get("uncertainty", 0.0):
            out[comp] = {
                "competency": comp,
                "importance": h.get("importance", 5),
                "uncertainty": competency_uncertainty,
                "placeholder_confidence": h.get("confidence", 0.5),
                "missing_evidence": h.get("missing_evidence", []),
            }
    return out