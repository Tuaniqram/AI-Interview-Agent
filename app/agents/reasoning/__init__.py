"""AURA V5 reasoning capabilities — pure belief machinery.

These modules are stateless functions over ``InterviewBrain`` fragments: they
consume hypothesis/evidence/evaluation dicts and return reasoning results.
They never read the database, never cache, and never mutate shared state — the
engine decides when to call them and how results are committed to the brain.

Capabilities:
- ``hypothesis_engine``  — priors, Bayesian belief updates, relevance, seeding
- ``information_gain``   — entropy-based target selection (EIG)
- ``evidence_engine``    — evidence records, competency summary, evidence graph
- ``contradiction_engine`` — score-inconsistency detection, sufficiency,
  hiring recommendation, next-action choice
- ``reflection_engine``  — node-shaped wrapper over the contradiction capability
"""
from app.agents.reasoning.hypothesis_engine import (  # noqa: F401
    generate_initial_hypotheses,
    update_hypotheses,
    bayesian_update,
    compute_relevance,
    hypothesis_node,
)
from app.agents.reasoning.information_gain import (  # noqa: F401
    expected_information_gain,
    next_target,
)
from app.agents.reasoning.evidence_engine import (  # noqa: F401
    build_evidence_records,
    update_evidence_graph,
    update_competency_summary,
    evidence_extractor_node,
)
from app.agents.reasoning.contradiction_engine import (  # noqa: F401
    detect_contradictions,
    evaluate_sufficiency,
    decide_next_action,
)
from app.agents.reasoning.reflection_engine import (  # noqa: F401
    reflection_engine,
)

__all__ = [
    "generate_initial_hypotheses",
    "update_hypotheses",
    "bayesian_update",
    "compute_relevance",
    "hypothesis_node",
    "expected_information_gain",
    "next_target",
    "build_evidence_records",
    "update_evidence_graph",
    "update_competency_summary",
    "evidence_extractor_node",
    "detect_contradictions",
    "evaluate_sufficiency",
    "decide_next_action",
    "reflection_engine",
]
