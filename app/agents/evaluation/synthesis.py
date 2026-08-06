"""V5 synthesis capability — builds the holistic final report.

Deterministic-first: the canonical composite (see
``contradiction_engine.compute_canonical_score`` / ``canonical_score_from_state``)
anchors every number in the report; the LLM writes narrative text only
(fit assessment, strengths, weaknesses, notes). Legacy V3 fields
(``rag_metadata.phase_decisions``, ``skills_tested``, ``skills_weak``,
``coverage_map``) are never read — they are null in V5 and were the source of
hallucinated holistic scores that contradicted the evidence graph.
"""
import json
import logging
import re

from app.core.interview_state import InterviewState

logger = logging.getLogger(__name__)

_MAX_HIGHLIGHTS = 5
_TOKEN_CHARS = "@:/\\`{}[]#"

# Evaluator process-buzzwords (P4): phrases about delivery style rather than
# demonstrated evidence. The summary's strengths/weaknesses must be anchored
# in competencies and their evidence — never generic interviewer impressions.
_BUZZWORD_RE = re.compile(
    r"\b(pacing|articulat\w*|eloquen\w*|fluenc\w*|fluent|rapport|enthusias\w*|"
    r"engagement|engaged|composure|demeanor|polite|pleasant|warmth|professional "
    r"manner)\b",
    re.IGNORECASE,
)


def _score_timeline(state: InterviewState) -> list[dict]:
    """Per-question average scores from the evidence store (V5 source of truth)."""
    per_question: dict[int, list[float]] = {}
    for ev in state.get("evidence_store") or []:
        q = int(ev.get("question_number", 0) or 0)
        if q > 0:
            per_question.setdefault(q, []).append(float(ev.get("score", 0.0) or 0.0))
    return [
        {
            "question": q,
            "score": round(sum(scores) / len(scores), 2),
        }
        for q, scores in sorted(per_question.items())
    ]


def _growth_trend(timeline: list[dict]) -> str:
    """First-half vs second-half trajectory from the score timeline."""
    scores = [t["score"] for t in timeline if t.get("score") is not None]
    if len(scores) < 3:
        return "stable"
    mid = len(scores) // 2
    first = sum(scores[:mid]) / mid
    second = sum(scores[mid:]) / (len(scores) - mid)
    if second - first > 0.5:
        return "improving"
    if first - second > 0.5:
        return "declining"
    return "stable"


def _clean_highlights(items: list, max_items: int = _MAX_HIGHLIGHTS) -> list[str]:
    """Dedupe highlights and drop artifacts (code tokens, paths, symbols).

    Rejects tokens like ``@angular/material:cdk`` that the evaluator extracted
    as noun phrases — they are not strengths or weaknesses.
    """
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in items or []:
        text = str(item).strip()
        if not text or len(text) < 3 or len(text) > 160:
            continue
        if any(ch in text for ch in _TOKEN_CHARS):
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= max_items:
            break
    return cleaned


def _aggregate_highlights(state: InterviewState) -> tuple[list[str], list[str]]:
    """Strengths/weaknesses aggregated and deduped from the evidence store."""
    strengths: list[str] = []
    weaknesses: list[str] = []
    for ev in state.get("evidence_store") or []:
        strengths.extend(ev.get("strengths") or [])
        weaknesses.extend(ev.get("weaknesses") or [])
    return _clean_highlights(strengths), _clean_highlights(weaknesses)


def _coverage_map(state: InterviewState) -> dict:
    return {
        comp: {
            "evidence_count": s.get("evidence_count", 0),
            "average_score": s.get("average_score", 0.0),
            "gap": s.get("gap", 1.0),
        }
        for comp, s in (state.get("competency_summary") or {}).items()
    }


def _evidence_strengths(summary: dict) -> list[str]:
    """Competency-anchored strengths: strong average backed by real evidence."""
    items = []
    for comp, s in sorted(summary.items()):
        count = int(s.get("evidence_count", 0) or 0)
        avg = float(s.get("average_score", 0.0) or 0.0)
        if count > 0 and avg >= 7.0:
            items.append(f"{comp}: strong evidence ({count} item(s), avg {avg:.1f}/10)")
    return items[: _MAX_HIGHLIGHTS]


def _evidence_weaknesses(summary: dict) -> list[str]:
    """Competency-anchored weaknesses: weak scores, evidence gaps, or no evidence."""
    items = []
    for comp, s in sorted(summary.items()):
        count = int(s.get("evidence_count", 0) or 0)
        avg = float(s.get("average_score", 0.0) or 0.0)
        gap = float(s.get("gap", 1.0) or 1.0)
        if count == 0:
            items.append(f"{comp}: no evidence gathered")
        elif avg < 5.0:
            items.append(f"{comp}: weak performance (avg {avg:.1f}/10)")
        elif gap >= 0.5:
            items.append(f"{comp}: evidence gap (gap {gap:.2f})")
    return items[: _MAX_HIGHLIGHTS]


def _filter_buzzwords(items: list) -> list[str]:
    """Drop delivery-style phrases; keep only evidence-anchored items."""
    return [
        text
        for text in items
        if not _BUZZWORD_RE.search(text)
    ]


def _merge_lists(*lists: list, cap: int = _MAX_HIGHLIGHTS) -> list[str]:
    """Order-preserving, deduplicated merge across the given lists."""
    seen: set[str] = set()
    merged: list[str] = []
    for lst in lists:
        for item in lst or []:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= cap:
                return merged
    return merged


def build_final_report(
    state: InterviewState,
    canonical: float,
    llm: dict | None = None,
) -> dict:
    """Assemble the final report from V5 state + optional LLM narrative.

    ``canonical`` is the single source of truth for the report's numbers —
    every score field mirrors it, so the report can never contradict the
    recommendation, the persisted ``final_score`` or the hiring decision.
    """
    timeline = _score_timeline(state)
    trend = _growth_trend(timeline)
    summary = state.get("competency_summary") or {}
    strengths, weaknesses = _aggregate_highlights(state)
    llm = llm or {}

    skills_tested = sorted(summary.keys())
    skills_weak = sorted(
        comp
        for comp, s in summary.items()
        if float(s.get("average_score", 0.0) or 0.0) < 5.0
        or float(s.get("gap", 1.0) or 1.0) >= 0.5
    )

    # P4: strengths/weaknesses are anchored in the competency evidence first;
    # LLM-drafted items count only when they are not delivery-style buzzwords.
    evidence_strengths = _evidence_strengths(summary)
    evidence_weaknesses = _evidence_weaknesses(summary)
    llm_strengths = _filter_buzzwords(_clean_highlights(llm.get("key_strengths")))
    llm_weaknesses = _filter_buzzwords(_clean_highlights(llm.get("key_weaknesses")))

    return {
        "holistic_score": canonical,
        "average_score": canonical,
        "growth_trend": trend,
        "narrative": llm.get("narrative", ""),
        "key_strengths": _merge_lists(
            evidence_strengths,
            llm_strengths or strengths[:3],
        ),
        "key_weaknesses": _merge_lists(
            evidence_weaknesses,
            llm_weaknesses or weaknesses[:3],
        ),
        "fit_assessment": llm.get("fit_assessment", "Potential Fit"),
        "interview_notes": llm.get("interview_notes", ""),
        "skills_tested": skills_tested,
        "skills_weak": skills_weak,
        "coverage_map": _coverage_map(state),
        "max_difficulty_reached": state.get("difficulty_level", 1),
        "score_timeline": timeline,
    }


async def synthesis_node(state: InterviewState) -> InterviewState:
    """
    Build the final report: canonical score anchors it, LLM narrates it.
    """
    from app.agents.reasoning.contradiction_engine import canonical_score_from_state
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    canonical = canonical_score_from_state(state) or 0.0
    job_role = state.get("job_role", "Unknown")
    timeline = _score_timeline(state)
    trend = _growth_trend(timeline)
    coverage_map = _coverage_map(state)
    strengths, weaknesses = _aggregate_highlights(state)

    llm: dict = {}
    try:
        llm_service = get_llm_service()

        synthesis_prompt = load_prompt(
            "evaluation",
            "synthesis.md",
            job_role=job_role,
            score_timeline=json.dumps(timeline, indent=2),
            avg_score=f"{canonical:.1f}",
            growth_trend=trend,
            max_difficulty=f"Level {state.get('difficulty_level', 1)}/3",
            skills_tested=json.dumps(sorted((state.get("competency_summary") or {}).keys()), indent=2)
            if state.get("competency_summary")
            else "None recorded",
            skills_weak=json.dumps(
                [
                    comp
                    for comp, s in (state.get("competency_summary") or {}).items()
                    if float(s.get("average_score", 0.0) or 0.0) < 5.0
                    or float(s.get("gap", 1.0) or 1.0) >= 0.5
                ],
                indent=2,
            )
            if state.get("competency_summary")
            else "None identified",
            coverage_map=json.dumps(coverage_map, indent=2)
            if coverage_map
            else "No coverage data",
            canonical_score=f"{canonical:.2f}",
            evidence_strengths=json.dumps(_evidence_strengths(state.get("competency_summary") or {}), indent=2)
            or "[]",
            evidence_weaknesses=json.dumps(_evidence_weaknesses(state.get("competency_summary") or {}), indent=2)
            or "[]",
        )

        response = await llm_service.invoke(
            prompt=synthesis_prompt,
            temperature=0.3,
            max_tokens=800,
            tier="strong",
        )

        from app.intelligence._helpers import parse_json

        try:
            data = parse_json(response)
        except ValueError:
            data = None

        if data:
            # Only narrative fields are accepted. ``holistic_score`` is
            # deliberately ignored — the canonical composite anchors the
            # report, never the LLM.
            llm = {
                key: data.get(key)
                for key in (
                    "narrative",
                    "fit_assessment",
                    "key_strengths",
                    "key_weaknesses",
                    "interview_notes",
                )
                if data.get(key) not in (None, "")
            }
    except Exception as e:  # noqa: BLE001 - fallback is fully deterministic
        logger.warning(f"Synthesis LLM failed ({e}); using deterministic report")

    report = build_final_report(state, canonical, llm or None)
    logger.info(
        f"Synthesis complete: holistic_score={report['holistic_score']}, "
        f"fit={report['fit_assessment']}"
    )

    return {
        **state,
        "final_report": report,
    }
