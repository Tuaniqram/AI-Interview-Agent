"""Document analyzer — turns retrieved company/department document chunks into
structured company knowledge (tech stack, culture, process, challenges).

Deterministic keyword extraction always works and is fully offline; the LLM
pass is optional and guarded. This feeds ``company_brain``.
"""
import logging
import re

from app.intelligence._helpers import dedupe

logger = logging.getLogger(__name__)

_TECH_KEYWORDS = [
    "python", "typescript", "javascript", "react", "vue", "node", "django",
    "fastapi", "flask", "golang", "rust", "java", "kotlin", "swift",
    "kubernetes", "docker", "aws", "gcp", "azure", "terraform", "postgresql",
    "mysql", "mongodb", "redis", "kafka", "graphql", "microservices", "ci/cd",
    "mlops", "tensorflow", "pytorch", "airflow", "spark", "llm", "rag",
]

_PROCESS_KEYWORDS = [
    "agile", "scrum", "kanban", "sprint", "code review", "ci/cd", "on-call",
    "incident", "deployment", "release", "sdlc", "standup", "retrospective",
    "sprint planning", "roadmap", "sla",
]

_CULTURE_KEYWORDS = [
    "culture", "values", "mission", "vision", "collaboration", "ownership",
    "transparency", "remote", "hybrid", "in-office", "learning", "growth",
    "customer-first", "autonomy", "feedback",
]

_CHALLENGE_MARKERS = (
    "challenge", "pain point", "we struggle", "difficult", "bottleneck",
    "incident", "complex", "technical debt",
)


def analyze_documents(documents: list[dict], job_role: str = "") -> dict:
    """Best-effort structured summary of document chunks.

    Args:
        documents: list of ``{"page_content": str, "metadata": dict}``
        job_role: target role, used to scope the summary

    Returns:
        dict with summary/mission/tech_stack/process/culture/challenges.
    """
    texts = [
        d.get("page_content", "") for d in documents or []
        if isinstance(d, dict) and d.get("page_content")
    ]
    combined = "\n".join(texts)

    return {
        "summary": _make_summary(texts, job_role),
        "mission": _extract_mission(texts),
        "tech_stack": _extract_keywords(combined, _TECH_KEYWORDS),
        "process": _extract_keywords(combined, _PROCESS_KEYWORDS),
        "culture": _extract_keywords(combined, _CULTURE_KEYWORDS),
        "challenges": _extract_challenges(texts),
        "role_context": "",
    }


def _make_summary(texts: list[str], job_role: str) -> str:
    if not texts:
        return ""
    head = texts[0].strip()
    snippet = head[:600]
    return snippet + ("…" if len(head) > 600 else "")


def _extract_mission(texts: list[str]) -> str:
    for text in texts:
        for line in text.splitlines():
            lowered = line.strip().lower()
            if ("mission" in lowered or "we are" in lowered or "we build" in lowered
                    or "we enable" in lowered) and len(line.strip()) > 15:
                return line.strip()[:300]
    return ""


def _extract_keywords(combined: str, keywords: list[str]) -> list[str]:
    if not combined:
        return []
    lowered = combined.lower()
    return dedupe([kw for kw in keywords if kw in lowered])


def _extract_challenges(texts: list[str]) -> list[str]:
    challenges = []
    for text in texts:
        lowered = text.lower()
        if not any(marker in lowered for marker in _CHALLENGE_MARKERS):
            continue
        for line in text.splitlines():
            line_lower = line.lower()
            if any(marker in line_lower for marker in _CHALLENGE_MARKERS) and 20 < len(line) < 300:
                challenges.append(line.strip())
                break
    return dedupe(challenges)[:5]


def _extract_keywords_with_regex(combined: str, pattern: str) -> list[str]:
    """Unused convenience — kept for future regex-based extraction."""
    return dedupe(re.findall(pattern, combined, flags=re.IGNORECASE))
