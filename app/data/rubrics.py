"""Family rubrics — T2 scoring.

Every interview family (technical + the 8 job families + cognitive/behavioral/
experience) gets a rubric: which dimensions are scored, at what weight, what a
high/medium/low score looks like (anchors), and which evidence keywords the F6
calibration trusts as "concrete". This is the single source of truth for the
deterministic scoring layer (``app/agents/evaluation/scoring.py``) and the
evaluator prompt rendering (``prompts/evaluation/unified_evaluator.md``).

Design rule (T1): family competencies lead with the ``domain`` dimension. The
tech rubric keeps ``technical`` as its primary dimension; every non-tech family
weights ``domain`` highest and drops ``technical`` to zero so the composite is
never inflated by a dimension the role does not exercise.
"""
from __future__ import annotations

# All dimensions the evaluator can score. ``domain`` is the family-primary
# dimension added in T2; ``technical`` is tech-primary.
RUBRIC_DIMENSIONS = (
    "technical",
    "domain",
    "communication",
    "reasoning",
    "behavioral",
    "confidence",
    "completeness",
)

# Generic band anchors per dimension, rendered into the evaluator prompt as the
# scoring guide. Shared across families; a family may override its primary
# dimension's anchors.
ANCHORS: dict[str, list[str]] = {
    "technical": [
        "9-10: mastery — correct, deep, tradeoff-aware, production-grounded",
        "7-8: strong — correct with minor gaps or shallow tradeoffs",
        "5-6: adequate — correct basics, some inaccuracy, little depth",
        "0-4: weak — incorrect or superficial",
    ],
    "domain": [
        "9-10: master of the field — current, decisive, grounded in real outcomes",
        "7-8: solid — clear working knowledge with a couple of soft spots",
        "5-6: partial — understands basics, struggles with nuance or current practice",
        "0-4: weak — confused or no real field knowledge",
    ],
    "communication": [
        "9-10: crisp, structured, concise; explains complex ideas simply",
        "7-8: clear with minor rambling or omitted structure",
        "5-6: understandable but disorganized or wordy",
        "0-4: confusing, unstructured, or unresponsive",
    ],
    "reasoning": [
        "9-10: logical, considers alternatives, cause-effect, depth of analysis",
        "7-8: coherent argument with some alternative consideration",
        "5-6: linear reasoning, misses alternatives or edge cases",
        "0-4: illogical, unsupported, or no reasoning shown",
    ],
    "behavioral": [
        "9-10: ownership and collaboration evidenced with concrete STAR detail",
        "7-8: clear example with responsibility and outcome",
        "5-6: describes activity without measurable ownership",
        "0-4: vague or no behavioral evidence",
    ],
    "confidence": [
        "9-10: calibrated certainty, honest about unknowns, pushes back well",
        "7-8: appropriately sure, some over- or under-confidence",
        "5-6: hesitant or overconfident without backing",
        "0-4: bluffing or constant hedging",
    ],
    "completeness": [
        "9-10: fully answers every part of the question",
        "7-8: covers the main parts, misses an edge case",
        "5-6: partial coverage, skips key sub-parts",
        "0-4: ignores most of the question",
    ],
}

# Evidence keywords that prove an answer is concrete (F6 calibration). Keyed by
# family; every family inherits the generic set and adds its own.
GENERIC_EVIDENCE_KEYWORDS = (
    "example", "project", "production", "incident", "trade-off", "tradeoffs",
    "trade offs", "architecture", "owned", "ownership", "scale", "scalability",
    "latency", "bottleneck",
)

FAMILY_EVIDENCE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "technical": (),
    "commerce": ("deal", "pipeline", "territory", "quota", "negotiation", "revenue", "close", "customer"),
    "marketing": ("campaign", "funnel", "seo", "content", "channel", "launch", "conversion", "brand"),
    "design": ("user", "figma", "prototype", "usability", "research", "interview", "journey", "wireframe"),
    "product": ("roadmap", "user story", "metric", "sprint", "launch", "backlog", "hypothesis", "interview"),
    "hr": ("hiring", "interview", "onboarding", "culture", "retention", "compensation", "policy", "talent"),
    "finance": ("model", "forecast", "budget", "margin", "cash flow", "audit", "variance", "pricing"),
    "operations": ("process", "kpi", "sla", "workflow", "vendor", "supply chain", "cost", "throughput"),
    "customer_success": ("churn", "retention", "onboarding", "renewal", "nps", "account", "expansion"),
    "behavioral": ("team", "mentor", "conflict", "decision", "stakeholder"),
    "cognitive": ("experiment", "tradeoff", "analysis", "option", "constraint"),
    "experience": ("project", "incident", "outage", "migration", "launch"),
}

GENERIC_OWNERSHIP_WORDS = (
    "architect", "architecture", "owner", "owned", "ownership", "define standards",
)

FAMILY_OWNERSHIP_WORDS: dict[str, tuple[str, ...]] = {
    "commerce": ("owned", "closed", "drove", "built", "led"),
    "marketing": ("owned", "built", "launched", "ran", "led"),
    "design": ("owned", "led", "facilitated", "shipped"),
    "product": ("owned", "shipped", "prioritized", "drove"),
    "hr": ("owned", "built", "ran", "designed", "resolved"),
    "finance": ("owned", "built", "modeled", "reviewed", "approved"),
    "operations": ("owned", "built", "ran", "improved", "managed"),
    "customer_success": ("owned", "saved", "grew", "turned around", "renewed"),
    "behavioral": ("owned", "led", "drove"),
    "cognitive": ("owned", "decided", "chose", "designed"),
    "experience": ("owned", "led", "shipped", "ran"),
    "technical": (),
}

# Family metrics the quantification check recognizes in addition to raw numbers.
GENERIC_QUANTIFICATION_TERMS = (
    "revenue", "margin", "roi", "mrr", "arr", "nps", "churn", "conversion",
    "cac", "ltv", "headcount", "budget", "ctr", "cohort", "response rate",
)

# Dimension weights per family. Every family weights ``domain`` highest and
# zeroes ``technical`` (T1 domain-first); the tech rubric keeps ``technical``.
FAMILY_WEIGHTS: dict[str, dict[str, float]] = {
    "technical": {
        "technical": 0.30,
        "reasoning": 0.25,
        "communication": 0.20,
        "confidence": 0.10,
        "behavioral": 0.10,
        "completeness": 0.05,
    },
    "behavioral": {
        "behavioral": 0.30,
        "communication": 0.25,
        "reasoning": 0.20,
        "completeness": 0.10,
        "confidence": 0.10,
        "technical": 0.05,
    },
    "cognitive": {
        "reasoning": 0.30,
        "technical": 0.25,
        "communication": 0.20,
        "confidence": 0.10,
        "behavioral": 0.10,
        "completeness": 0.05,
    },
    "experience": {
        "domain": 0.30,
        "technical": 0.25,
        "reasoning": 0.20,
        "communication": 0.10,
        "confidence": 0.10,
        "behavioral": 0.05,
    },
    "commerce": {
        "domain": 0.30,
        "communication": 0.20,
        "reasoning": 0.20,
        "behavioral": 0.15,
        "confidence": 0.05,
        "completeness": 0.10,
    },
    "marketing": {
        "domain": 0.30,
        "completeness": 0.20,
        "communication": 0.15,
        "reasoning": 0.15,
        "behavioral": 0.10,
        "confidence": 0.10,
    },
    "design": {
        "domain": 0.30,
        "communication": 0.25,
        "reasoning": 0.20,
        "completeness": 0.10,
        "behavioral": 0.10,
        "confidence": 0.05,
    },
    "product": {
        "domain": 0.30,
        "reasoning": 0.25,
        "communication": 0.20,
        "completeness": 0.10,
        "behavioral": 0.10,
        "confidence": 0.05,
    },
    "hr": {
        "domain": 0.30,
        "behavioral": 0.25,
        "communication": 0.20,
        "reasoning": 0.10,
        "completeness": 0.10,
        "confidence": 0.05,
    },
    "finance": {
        "domain": 0.30,
        "reasoning": 0.25,
        "completeness": 0.15,
        "communication": 0.10,
        "behavioral": 0.10,
        "confidence": 0.10,
    },
    "operations": {
        "domain": 0.30,
        "completeness": 0.20,
        "reasoning": 0.20,
        "communication": 0.15,
        "behavioral": 0.10,
        "confidence": 0.05,
    },
    "customer_success": {
        "domain": 0.30,
        "communication": 0.25,
        "behavioral": 0.15,
        "completeness": 0.10,
        "reasoning": 0.10,
        "confidence": 0.10,
    },
}

# Category aliases -> rubric key (resolver categories match rubric keys).
_CATEGORY_KEY_MAP = {
    "technical": "technical",
    "behavioral": "behavioral",
    "cognitive": "cognitive",
    "experience": "experience",
    "commerce": "commerce",
    "com_": "commerce",
    "marketing": "marketing",
    "mkt_": "marketing",
    "design": "design",
    "des_": "design",
    "product": "product",
    "prd_": "product",
    "hr": "hr",
    "hr_": "hr",
    "finance": "finance",
    "fin_": "finance",
    "operations": "operations",
    "ops_": "operations",
    "customer_success": "customer_success",
    "cs_": "customer_success",
}

# Family rubric primary dimension label for the prompt.
FAMILY_LABELS: dict[str, str] = {
    "technical": "Technical Knowledge",
    "behavioral": "Behavioral Fit",
    "cognitive": "Cognitive & Analytical",
    "experience": "Experience & Execution",
    "commerce": "Commerce & Sales",
    "marketing": "Marketing & Growth",
    "design": "Design & UX",
    "product": "Product Management",
    "hr": "HR & People",
    "finance": "Finance & Accounting",
    "operations": "Operations",
    "customer_success": "Customer Success",
}

DEFAULT_RUBRIC_KEY = "technical"


def normalize_category(category: str | None) -> str:
    """Map a resolver category (or competency prefix) onto a rubric key."""
    if not category:
        return DEFAULT_RUBRIC_KEY
    key = _CATEGORY_KEY_MAP.get(str(category).strip().lower())
    if key in FAMILY_WEIGHTS:
        return key
    # Fall back on the family prefix embedded in an id like ``mkt_xyz``.
    for prefix, key in _CATEGORY_KEY_MAP.items():
        if prefix.endswith("_") and str(category).startswith(prefix):
            return key
    return DEFAULT_RUBRIC_KEY


def rubric_for_category(category: str | None) -> str:
    """Rubric key for a taxonomy category."""
    return normalize_category(category)


def dimension_weights(category: str | None, overrides: dict | None = None) -> dict[str, float]:
    """Dimension weights for a family, merged with style-level overrides.

    Missing dimensions get weight 0 (so a family role never scores on a
    dimension it does not exercise). ``overrides`` may replace any entry the
    family already weights — they can re-emphasize an active dimension but
    cannot resurrect a zeroed one, so the default tech-centric style weights
    never re-enable ``technical`` for a domain-first family role.
    """
    key = normalize_category(category)
    weights = dict(FAMILY_WEIGHTS[key])
    weights.setdefault("domain", 0.0)
    weights.setdefault("technical", 0.0)
    if overrides:
        for dim, w in overrides.items():
            if (
                dim in RUBRIC_DIMENSIONS
                and isinstance(w, (int, float))
                and weights.get(dim, 0.0) > 0
            ):
                weights[dim] = float(w)
    total = sum(weights.values()) or 1.0
    return {dim: round(w / total, 4) for dim, w in weights.items()}


def active_dimensions(category: str | None) -> list[str]:
    """Dimensions a family actually scores (weight > 0), in rubric order.

    Tech rubrics omit ``domain``; non-tech family rubrics omit ``technical`` —
    the evaluator only emits the dimensions that count, so a composite is never
    inflated by a dimension the role does not exercise.
    """
    weights = dimension_weights(category)
    return [dim for dim in RUBRIC_DIMENSIONS if weights.get(dim, 0.0) > 0]


def category_from_taxonomy(taxonomy: list | None, target: str | None) -> str | None:
    """Category of a competency id within a session taxonomy, or ``None``."""
    if target and isinstance(taxonomy, list):
        for comp in taxonomy:
            if isinstance(comp, dict) and comp.get("id") == target:
                return comp.get("category")
    return None


def evidence_keywords(category: str | None) -> tuple[str, ...]:
    key = normalize_category(category)
    return GENERIC_EVIDENCE_KEYWORDS + FAMILY_EVIDENCE_KEYWORDS.get(key, ())


def ownership_words(category: str | None) -> tuple[str, ...]:
    key = normalize_category(category)
    return GENERIC_OWNERSHIP_WORDS + FAMILY_OWNERSHIP_WORDS.get(key, ())


def quantification_terms(category: str | None) -> tuple[str, ...]:
    return GENERIC_QUANTIFICATION_TERMS


def anchors(category: str | None) -> dict[str, list[str]]:
    """Band anchors for a family's scored dimensions."""
    key = normalize_category(category)
    weights = dimension_weights(category)
    return {
        dim: ANCHORS.get(dim, ANCHORS["technical"])
        for dim in RUBRIC_DIMENSIONS
        if weights.get(dim, 0.0) > 0
    }


def render_rubric(category: str | None, label: str | None = None) -> str:
    """Human-readable rubric block for the evaluator prompt."""
    key = normalize_category(category)
    fam_label = label or FAMILY_LABELS.get(key, key.title())
    weights = dimension_weights(category)
    lines = [f"Rubric: {fam_label} — scored dimensions in order of weight:"]
    for dim in sorted(weights, key=lambda d: -weights[d]):
        if weights[dim] <= 0:
            continue
        lines.append(f"- {dim} ({weights[dim]:.0%} weight):")
        for anchor in anchors(category).get(dim, ()):
            lines.append(f"    {anchor}")
    return "\n".join(lines)


def domain_label_for(category: str | None) -> str:
    """The primary dimension label used as the evaluator's knowledge dimension."""
    key = normalize_category(category)
    return FAMILY_LABELS.get(key, "Technical Knowledge")
