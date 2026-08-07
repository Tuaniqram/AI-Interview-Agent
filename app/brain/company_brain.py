"""Company Brain V5 — the context layer.

Purpose: answer "what kind of engineer succeeds here?" with engineering DNA,
not just a tech stack. Everything is derived deterministically from the
existing company brain (tech stack, process, culture, focus areas) plus the
role being hired. No new LLM calls.
"""
import logging

logger = logging.getLogger(__name__)

SENIORITY_KEYWORDS = {
    "junior": ("junior", "entry", "graduate", "intern", "trainee"),
    "mid": ("mid", "intermediate", "regular", "level 2"),
    "senior": ("senior", "principal", "staff", "lead", "architect", "sr"),
}

# --------------------------------------------------------------------------- #
# Deterministic engineering-DnA derivations (keyword heuristics)              #
# --------------------------------------------------------------------------- #

_SPEED_VS_QUALITY = [
    (("experimentation", "fast shipping", "speed", "weekly release"), "speed_first"),
    (("review", "reliable", "test", "quality", "reliability", "standards"), "quality_first"),
]

_ARCHITECTURE_STYLE = [
    (("kubernetes", "microservice", "container", "cloud", "aws", "gcp", "azure"), "distributed_services"),
    (("monolith", "monolithic", "service-", "modular"), "modular_monolith"),
    (("serverless", "lambda", "event-driven"), "event_driven_services"),
    (("saas", "multi-tenant"), "multi_tenant_services"),
]

_OWNERSHIP_MODEL = [
    (("ownership", "own"), "strong_ownership"),
    (("squad", "autonomous", "cross-functional"), "autonomous_teams"),
    (("shared",), "shared_ownership"),
]

_CULTURE_SIGNALS = [
    ("ownership", "ownership"),
    ("experimentation", "experimentation"),
    ("research", "research mindset"),
    ("collaborat", "collaborative"),
    ("invest", "long-term thinking"),
    ("customer", "customer focus"),
]

_FAILURE_PATTERNS = [
    "clickers who only implement assigned tickets",
    "no tradeoff discussion in designs",
    "cannot explain why a decision was made",
    "no production / operational experience",
    "milestone-driven without ownership",
]


def _matches(text: str, keywords: tuple) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def infer_engineering_philosophy(company_brain: dict) -> dict:
    raw = " ".join(
        str(x)
        for x in [
            company_brain.get("tech_stack") or [],
            company_brain.get("process") or [],
            company_brain.get("culture") or [],
            company_brain.get("focus_areas") or [],
            company_brain.get("architect_decision") or [],
            company_brain.get("summary") or "",
        ]
    ).lower()

    speed_vs_quality = "balanced"
    for kws, val in _SPEED_VS_QUALITY:
        if _matches(raw, kws):
            speed_vs_quality = val
            break

    architecture_style = "monolith"
    for kws, val in _ARCHITECTURE_STYLE:
        if _matches(raw, kws):
            architecture_style = val
            break

    ownership_model = "shared_ownership"
    for kws, val in _OWNERSHIP_MODEL:
        if _matches(raw, kws):
            ownership_model = val
            break

    return {
        "speed_vs_quality": speed_vs_quality,
        "architecture_style": architecture_style,
        "ownership_model": ownership_model,
    }


def infer_culture_signals(company_brain: dict) -> list[str]:
    raw = " ".join(
        str(x) for x in [company_brain.get("culture") or [], company_brain.get("focus_areas") or [], company_brain.get("summary") or ""]
    ).lower()
    return [label for kw, label in _CULTURE_SIGNALS if kw in raw]


def build_v5_company_brain(company_brain: dict, job_role: str = "") -> dict:
    """Enrich a V4 company brain with the V5 company DNA fields.

    Returns a company_brain with ``engineering_philosophy``,
    ``technical_expectations``, ``failure_patterns``, ``culture_signals`` and
    ``senior_expectations``. Always succeeds — missing source material yields
    conservative defaults.
    """
    base = dict(company_brain or {})
    role_label = infer_seniority_label(job_role) or "senior"
    philosophy = infer_engineering_philosophy(base)

    expectations_by_level = {
        level: {
            "expected_behavior": infer_expectations_for_level(level, philosophy),
        }
        for level in ("junior", "mid", "senior")
    }

    enriched = {
        **base,
        "engineering_philosophy": philosophy,
        "technical_expectations": expectations_by_level,
        "senior_expectations": infer_expectations_for_level(role_label, philosophy),
        "culture_signals": infer_culture_signals(base),
        "failure_patterns": {
            "avoid": _FAILURE_PATTERNS,
        },
    }
    return enriched


def infer_seniority_label(job_role: str) -> str | None:
    lowered = (job_role or "").lower()
    for label, kws in SENIORITY_KEYWORDS.items():
        if any(kw in lowered for kw in kws):
            return label
    return None


def infer_expectations_for_level(level: str, philosophy: dict) -> list[str]:
    base = {
        "junior": [
            "complete code review cycles",
            "follow team standards",
            "raise questions about ambiguity",
        ],
        "mid": [
            "design within an owned service or component",
            "deploy and operate what you ship",
            "don't leave final decisions undiscussed",
        ],
        "senior": [
            "design independently",
            "mentor others",
            "handle ambiguity",
            "debate tradeoffs with evidence",
            "own production systems",
        ],
    }.get(level, ["design independently", "own production systems"])
    if philosophy.get("speed_vs_quality") == "quality_first":
        base.append("prioritize reliability and measurement")
    if philosophy.get("ownership_model") == "strong_ownership":
        base.append("take end-to-end ownership")
    return base