"""V5 contradiction engine — the reflection capability.

Pure functions that detect score inconsistencies, weigh competency coverage,
judge evidence sufficiency, derive a hiring recommendation and pick the next
interview action. The engine (via ``reflection_engine``) orchestrates them and
commits the results to the ``InterviewBrain``.
"""
import logging
from uuid import uuid4
from datetime import datetime, timezone

from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.data.competency_resolver import derive_required_competencies

logger = logging.getLogger(__name__)

COVERAGE_THRESHOLD = 0.7
MIN_QUESTIONS_PER_COMPETENCY = 2
# Fix 11: the interview can never finish before this many answered questions —
# a hiring decision needs a minimum evidence base regardless of saturation or
# coverage signals (safety net against premature finals).
MIN_QUESTIONS_BEFORE_FINISH = 5
# Fix 7: a competency is never asked more than this many questions — beyond it
# the same area gets re-probed with marginal new information.
MAX_QUESTIONS_PER_COMPETENCY = 3
MAX_CONSECUTIVE_SAME_DIMENSION = 2
SUFFICIENCY_GAP_THRESHOLD = 0.3
# Confidence multiplier floor — verdict confidence never drops below 50% of the
# raw ratio even when evidence-confidence metadata is missing.
CONFIDENCE_QUALITY_FLOOR = 0.5
# Reaching the top difficulty (5 levels, Fix 8) with decent coverage is a
# strong signal the interview has probed far enough to decide.
HIGH_DIFFICULTY_FINISH = 5

# Fix 6: fallback required set mirrors the session default — the HIGH/MEDIUM
# subset capped at 6 — so coverage/sufficiency never targets the whole
# taxonomy (which kept coverage near 0%).
_DEFAULT_REQUIRED = derive_required_competencies(COMPETENCY_TAXONOMY)

__all__ = [
    "COVERAGE_THRESHOLD",
    "MIN_QUESTIONS_PER_COMPETENCY",
    "MIN_QUESTIONS_BEFORE_FINISH",
    "MAX_QUESTIONS_PER_COMPETENCY",
    "MAX_CONSECUTIVE_SAME_DIMENSION",
    "SUFFICIENCY_GAP_THRESHOLD",
    "CONFIDENCE_QUALITY_FLOOR",
    "HIGH_DIFFICULTY_FINISH",
    "competency_weights",
    "competency_question_counts",
    "detect_contradictions",
    "evaluate_sufficiency",
    "decide_next_action",
    "average_evidence_confidence",
    "unanswered_hypothesis_count",
]


def competency_question_counts(questions_asked: list) -> dict[str, int]:
    """Per-competency question counts from the asked-question history (Fix 7)."""
    counts: dict[str, int] = {}
    for q in questions_asked or []:
        comp = q.get("competency", "") if isinstance(q, dict) else ""
        if comp:
            counts[comp] = counts.get(comp, 0) + 1
    return counts


def competency_weights(state: dict) -> dict[str, float]:
    taxonomy = state.get("competency_taxonomy") or COMPETENCY_TAXONOMY
    weights = {}
    for c in taxonomy:
        weight = c.get("weight")
        weights[c["id"]] = float(weight) if weight else 1.0
    return weights


def average_evidence_confidence(competency_summary: dict) -> float:
    """Evidence-count-weighted average confidence across competencies (0..1)."""
    total_count = 0
    weighted = 0.0
    for summary in (competency_summary or {}).values():
        count = int(summary.get("evidence_count", 0) or 0)
        avg_conf = float(summary.get("average_confidence", 0.0) or 0.0)
        total_count += count
        weighted += avg_conf * count
    if total_count == 0:
        return 0.0
    return round(weighted / total_count, 4)


def unanswered_hypothesis_count(hypotheses: list) -> int:
    """Hypotheses still open (untested or testing) — not yet resolved."""
    return sum(1 for h in hypotheses if h.get("status") in ("untested", "testing"))


def detect_contradictions(
    competency_summary: dict,
    existing_contradictions: list,
    existing_consistency: list,
    unified_evaluation: dict,
) -> tuple[list, list]:
    contradictions = list(existing_contradictions)
    consistency_checks = list(existing_consistency)

    evaluation = unified_evaluation or {}
    for dim, data in evaluation.items():
        if not isinstance(data, dict):
            continue
        score = data.get("score")
        if score is None:
            continue
        evidence = data.get("evidence", "")
        confidence = data.get("confidence", 0.5)

        if score >= 7.0 and confidence >= 0.3:
            consistency_checks.append({
                "type": dim,
                "assessment": "positive",
                "score": score,
                "confidence": confidence,
                "evidence": evidence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    for comp, summary in competency_summary.items():
        scores = summary.get("scores", [])
        if len(scores) >= 2:
            latest = scores[-1]
            prev = scores[-2]
            if latest is not None and prev is not None and abs(latest - prev) >= 4.0:
                contradiction_id = str(uuid4())
                contradictions.append({
                    "id": contradiction_id,
                    "competency": comp,
                    "type": "score_inconsistency",
                    "statement": (
                        f"Inconsistent performance in {comp}: previous score {prev}, latest {latest}"
                    ),
                    "severity": "medium",
                    "evidence_ids": [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    return contradictions, consistency_checks


def evaluate_sufficiency(
    competency_summary: dict,
    required_competencies: list[str],
    contradictions: list,
    hypotheses: list,
    question_number: int,
    comp_weights: dict[str, float],
    difficulty_reached: int | None = None,
    unanswered_hypotheses: int = 0,
) -> tuple[dict, dict]:
    total_weight = 0.0
    covered_weight = 0.0
    comp_details = {}

    # Only consider required competencies that exist in the competency_weights
    # (i.e. were resolved into the runtime taxonomy). This prevents unknown
    # blueprint IDs from inflating the denominator and keeping coverage low.
    if required_competencies:
        filtered_required = [c for c in required_competencies if c in comp_weights]
    else:
        filtered_required = []
    if not filtered_required:
        # fallback to all known competencies in the taxonomy
        filtered_required = list(comp_weights.keys())

    for comp in filtered_required:
        summary = competency_summary.get(comp, {})
        evidence_count = summary.get("evidence_count", 0)
        avg_score = summary.get("average_score", 0.0) or 0.0
        gap = summary.get("gap", 1.0)

        weight = comp_weights.get(comp, 1.0)

        is_covered = (
            evidence_count >= MIN_QUESTIONS_PER_COMPETENCY
            and gap <= SUFFICIENCY_GAP_THRESHOLD
        )
        if is_covered:
            covered_weight += weight
        total_weight += weight

        comp_details[comp] = {
            "evidence_count": evidence_count,
            "average_score": avg_score,
            "gap": gap,
            "weight": weight,
            "covered": is_covered,
        }

    coverage_ratio = covered_weight / total_weight if total_weight > 0 else 0.0

    serious_contradictions = [
        c for c in contradictions if c.get("severity") in ("high", "medium")
    ]
    severity = "sufficient" if serious_contradictions else "insufficient"

    avg_confidence = average_evidence_confidence(competency_summary)

    if coverage_ratio >= COVERAGE_THRESHOLD and not serious_contradictions and question_number >= 5:
        sufficiency = {
            "is_sufficient": True,
            "coverage_ratio": round(coverage_ratio, 2),
            "covered_weight": covered_weight,
            "total_weight": total_weight,
            "remaining_gaps": sum(1 for d in comp_details.values() if not d["covered"]),
            "severity": "sufficient",
            "average_confidence": avg_confidence,
            "difficulty_reached": difficulty_reached,
            "unanswered_hypotheses": unanswered_hypotheses,
            "details": comp_details,
        }
    else:
        sufficiency = {
            "is_sufficient": False,
            "coverage_ratio": round(coverage_ratio, 2),
            "covered_weight": covered_weight,
            "total_weight": total_weight,
            "remaining_gaps": sum(1 for d in comp_details.values() if not d["covered"]),
            "severity": severity,
            "average_confidence": avg_confidence,
            "difficulty_reached": difficulty_reached,
            "unanswered_hypotheses": unanswered_hypotheses,
            "details": comp_details,
        }

    hypothesis_statuses = {}
    for h in hypotheses:
        st = h.get("status", "untested")
        hypothesis_statuses[st] = hypothesis_statuses.get(st, 0) + 1

    confirmed = hypothesis_statuses.get("confirmed", 0)
    refuted = hypothesis_statuses.get("refuted", 0)
    testing = hypothesis_statuses.get("testing", 0)

    # Quality multiplier: temper verdict confidence by how confident the
    # collected evidence itself is (floored so missing metadata never zeroes it).
    quality = max(avg_confidence, CONFIDENCE_QUALITY_FLOOR)

    # Hypothesis resolution ratio: resolved hypotheses (confirmed+refuted) / total
    total_hypotheses = len(hypotheses or [])
    resolved = confirmed + refuted
    resolved_ratio = (resolved / total_hypotheses) if total_hypotheses > 0 else 0.0

    # Competency average score (weighted) on 0..10 scale
    competency_average_score = (
        sum(d["average_score"] * d["weight"] for d in comp_details.values()) / total_weight
        if total_weight > 0
        else 0.0
    )

    # hypothesis_confidence in 0..1
    if confirmed + refuted > 0:
        hypothesis_confidence = confirmed / (confirmed + refuted)
    else:
        # fallback to overall evidence confidence when no hypotheses resolved
        hypothesis_confidence = avg_confidence if avg_confidence > 0 else 0.5

    # coverage_ratio already computed (0..1)

    # Final scoring: scale hypothesis_confidence and coverage to 0..10 before weighting
    # so final_score is on 0..10 range. Interpreting the requested formula to
    # keep a 0..10 composite.
    final_score = round(
        competency_average_score * 0.5
        + (hypothesis_confidence * 10.0) * 0.3
        + (coverage_ratio * 10.0) * 0.2,
        2,
    )

    # Verdict mapping based on final_score thresholds
    if final_score >= 8.5:
        verdict = "strong_hire"
    elif 7.5 <= final_score < 8.5:
        verdict = "hire"
    elif 6.5 <= final_score < 7.5:
        verdict = "borderline"
    elif 5.0 <= final_score < 6.5:
        verdict = "weak"
    else:
        verdict = "reject"

    # Legacy confidence computation (preserved for backward compatibility/tests):
    legacy_confidence = 0.0
    if confirmed + refuted > 0:
        legacy_confidence = (
            round(min(confirmed / (confirmed + refuted + 1) * quality, 0.95), 2)
            if confirmed > 0
            else 0.5
        ) if confirmed >= refuted else (
            round(min(refuted / (confirmed + refuted + 1) * quality, 0.95), 2)
            if refuted > 0
            else 0.5
        )

    # Confidence: combine evidence quality and resolved ratio, dampened by contradictions
    base_confidence = quality * (resolved_ratio if resolved_ratio > 0 else 0.5)
    # reduce confidence if there are serious contradictions
    serious_contradictions = [c for c in contradictions if c.get("severity") in ("high", "medium")]
    contradiction_penalty = min(0.4, 0.1 * len(serious_contradictions))
    confidence_v2 = round(max(0.0, min(1.0, base_confidence * (1.0 - contradiction_penalty))), 2)

    # Do not return 'insufficient_evidence' when coverage and hypothesis resolution meet thresholds
    if coverage_ratio >= 0.7 and resolved_ratio >= 0.7:
        # allow verdict determined by score above
        pass
    else:
        # If we lack sufficient coverage/resolution, fall back to previous logic
        if coverage_ratio < COVERAGE_THRESHOLD or question_number < MIN_QUESTIONS_BEFORE_FINISH:
            verdict = "insufficient_evidence"
            legacy_confidence = 0.0
            confidence_v2 = 0.0

    recommendation = {
        "verdict": verdict,
        # Preserve legacy 'confidence' field expected by legacy callers/tests
        "confidence": legacy_confidence,
        # Also expose the newer blended confidence under a different key for observability
        "confidence_v2": confidence_v2,
        "coverage_ratio": round(coverage_ratio, 2),
        "composite_score": final_score,
        "confirmed_hypotheses": confirmed,
        "refuted_hypotheses": refuted,
        "testing_hypotheses": testing,
        "contradictions_found": len(contradictions),
        "average_confidence": avg_confidence,
        "difficulty_reached": difficulty_reached,
        "unanswered_hypotheses": unanswered_hypotheses,
    }

    logger.debug(
        f"[RECOMMENDATION] coverage={round(coverage_ratio,2)} confidence_v2={confidence_v2} legacy_confidence={legacy_confidence} final_score={final_score}"
    )

    return sufficiency, recommendation


def decide_next_action(
    competency_summary: dict,
    required_competencies: list[str],
    evidence_sufficiency: dict,
    contradictions: list,
    question_number: int,
    hypotheses: list,
    difficulty_reached: int | None = None,
    unanswered_hypotheses: int = 0,
    question_counts: dict | None = None,
    last_competency: str | None = None,
) -> str:
    if evidence_sufficiency.get("is_sufficient"):
        # Fix 11: hard floor — never finish before enough questions were
        # answered to justify a decision, whatever the signals say.
        if question_number >= MIN_QUESTIONS_BEFORE_FINISH:
            return "finish"
        return "probe"

    if question_number <= 2:
        return "probe"

    # Fix 10: finish when every required competency is covered (evidence >=
    # minimum, no gap) and no required hypothesis is still open and overall
    # confidence is strong enough to decide. Checked before the generic
    # saturation rule: full required coverage trumps "everything settled"
    # rotation.
    required_open = any(
        h.get("status") in ("untested", "testing")
        for h in (hypotheses or [])
        if h.get("competency") in required_competencies
    )
    all_required_covered = all(
        int((competency_summary.get(comp, {}) or {}).get("evidence_count", 0) or 0)
        >= MIN_QUESTIONS_PER_COMPETENCY
        for comp in required_competencies
    )
    if (
        required_competencies
        and question_number >= MIN_QUESTIONS_BEFORE_FINISH
        and all_required_covered
        and not required_open
        and average_evidence_confidence(competency_summary) >= 0.6
    ):
        return "finish"

    # Saturation (AURA V5): every hypothesis is settled — keep asking would
    # only repeat the same questions, so rotate to a fresh competency (the
    # planner seeds a new hypothesis for it) or finish once nothing remains.
    open_hypotheses = [
        h for h in (hypotheses or [])
        if h.get("status") in ("untested", "testing")
    ]
    if hypotheses and not open_hypotheses:
        # All hypotheses settled. If we've answered enough questions, finish;
        # otherwise rotate to allow probing any uncovered competencies before final.
        if question_number >= MIN_QUESTIONS_BEFORE_FINISH:
            return "finish"
        return "change_competency"

    # Fix 7: per-competency question cap — a competency already asked
    # MAX_QUESTIONS_PER_COMPETENCY times rotates away instead of being
    # re-probed with repeating questions.
    counts = question_counts or {}
    if (
        last_competency
        and counts.get(last_competency, 0) >= MAX_QUESTIONS_PER_COMPETENCY
    ):
        return "change_competency"

    # Coverage-driven rotation: a competency with its minimum evidence and no
    # meaningful gap is done — move on to the next uncovered competency instead
    # of re-probing it.
    uncovered_exists = False
    any_covered = False
    for comp in required_competencies:
        summary = competency_summary.get(comp, {})
        gap = summary.get("gap")
        gap = float(gap) if gap is not None else 1.0
        covered = (
            int(summary.get("evidence_count", 0) or 0) >= MIN_QUESTIONS_PER_COMPETENCY
            and gap <= SUFFICIENCY_GAP_THRESHOLD
        )
        if covered:
            any_covered = True
        else:
            uncovered_exists = True
    if any_covered and uncovered_exists:
        return "change_competency"

    serious = [c for c in contradictions if c.get("severity") in ("high", "medium")]
    if len(serious) >= 2:
        return "change_competency"

    max_questions = 14  # AURA cap — evidence-driven end usually fires earlier
    if question_number >= max_questions:
        return "finish"

    # Top difficulty + decent coverage + at least 5 questions = pushed far
    # enough to decide without burning the remaining budget.
    coverage_ratio = evidence_sufficiency.get("coverage_ratio", 0.0)
    if (
        difficulty_reached
        and difficulty_reached >= HIGH_DIFFICULTY_FINISH
        and coverage_ratio >= COVERAGE_THRESHOLD
        and question_number >= 5
    ):
        return "finish"

    return "probe"
