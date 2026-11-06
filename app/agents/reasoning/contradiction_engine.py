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

# HACK: High-priority competency IDs based on taxonomy order and general importance
# This overlays priority logic for the coverage finish check
_HIGH_PRIORITY_IDS = {
    # Technical (highest immediate impact)
    "tech_core", "tech_system_design", "tech_data", "behav_teamwork",
    # Behavioral
    "behav_communication",
}
_HIGH_MIDS = {
    "tech_framework", "tech_db", "behav_leadership", "behav_conflict",
    "cog_problem_solving", "cog_analytical",
}

# Fix: Reduce coverage threshold from 0.7 to 0.5 to allow early-stage interviews
# to progress with partial competency coverage (was too restrictive at 70%)
COVERAGE_THRESHOLD = 0.5
# Keep minimum at 2 to avoid very shallow probing
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

# V5 hypothesis confidence: only hypotheses that were actually TESTED may
# count toward the confirmation ratio. Untested hypotheses dilute it, so a
# candidate whose claims were never probed cannot carry a 100% confirmation
# bonus regardless of how many weak claims were "confirmed" along the way.
def resolved_hypothesis_confidence(confirmed: int, refuted: int, untested: int, fallback: float) -> float:
    """confirmed / (confirmed + refuted + untested); fallback when nothing tested."""
    tested = int(confirmed or 0) + int(refuted or 0) + int(untested or 0)
    if tested > 0:
        return int(confirmed or 0) / tested
    return float(fallback)

# F5: the composite's bonus terms (hypothesis confidence, coverage) may lift a
# candidate at most this far above the demonstrated competency average.
COMPOSITE_CEILING_ABOVE_AVERAGE = 1.5

# V5 role gate: an interview may only finish once it pushed the candidate
# across most of the required set. 80% over the resolved blueprint is the
# "senior hire needs breadth" floor — 5 required competencies need 8+ answers.
FINISH_MIN_COVERAGE = 0.8

# V5 difficulty caps: evidence earned without being pushed is discounted.
# A session that never left the floor cannot produce the top verdicts —
# same philosophy as the decision engine's difficulty credit, applied to the
# recommendation scale so the two layers never disagree.
_DIFFICULTY_VERDICT_CAPS = {1: "borderline", 2: "borderline", 3: "hire", 4: "hire"}
_DIFFICULTY_VERDICT_ORDER = ("reject", "weak", "borderline", "hire", "strong_hire")

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


def compute_canonical_score(
    competency_average_score: float,
    hypothesis_confidence: float,
    coverage_ratio: float,
) -> float:
    """The single canonical 0..10 composite every downstream component must use.

    Blends the evidence-weighted competency average (0.5), hypothesis
    resolution confidence scaled to 0..10 (0.3) and coverage scaled to 0..10
    (0.2). This is THE canonical score: the recommendation's ``composite_score``,
    the persisted session ``final_score``, the synthesis ``holistic_score`` and
    the hiring-decision anchor all read from this one formula so the report can
    never show competing truths.

    F5 ceiling: the composite may never exceed the demonstrated competency
    average by more than ``COMPOSITE_CEILING_ABOVE_AVERAGE``. Confidence and
    coverage are refinements — they can push a strong performer to the top of
    their demonstrated band, but they can never rescue a candidate whose raw
    evidence sits below the bar. Without the cap, a candidate averaging 6.5
    but claiming 100% hypothesis confirmation and 100% coverage would score
    8.25 and be "hired" on bonuses alone.
    """
    composite = (
        float(competency_average_score) * 0.5
        + (float(hypothesis_confidence) * 10.0) * 0.3
        + (float(coverage_ratio) * 10.0) * 0.2
    )
    ceiling = float(competency_average_score) + COMPOSITE_CEILING_ABOVE_AVERAGE
    return round(min(composite, ceiling), 2)


def canonical_score_from_state(state: dict) -> float | None:
    """The canonical composite for a session, sourced from the live state.

    Returns the engine's ``hiring_recommendation.composite_score`` when present;
    otherwise recomputes it from the competency summary, hypotheses and
    coverage (so reporting stages that run before a recommendation still anchor
    on the same formula).
    """
    rec = state.get("hiring_recommendation") or {}
    score = rec.get("composite_score")
    if score is not None:
        return round(float(score), 2)

    summary = state.get("competency_summary") or {}
    hypotheses = state.get("hypotheses") or []
    weights = competency_weights(state)
    required = state.get("required_competencies") or list(weights.keys())
    total_weight = 0.0
    weighted_sum = 0.0
    for comp in required:
        weight = weights.get(comp, 1.0)
        total_weight += weight
        weighted_sum += (
            float(summary.get(comp, {}).get("average_score", 0.0) or 0.0) * weight
        )
    competency_average = weighted_sum / total_weight if total_weight > 0 else 0.0

    confirmed = sum(1 for h in hypotheses if h.get("status") == "confirmed")
    refuted = sum(1 for h in hypotheses if h.get("status") == "refuted")
    untested = sum(1 for h in hypotheses if h.get("status") == "untested")
    hypothesis_confidence = resolved_hypothesis_confidence(
        confirmed,
        refuted,
        untested,
        average_evidence_confidence(summary) or 0.5,
    )

    coverage = rec.get("coverage_ratio")
    if coverage is None:
        covered = sum(
            1
            for comp in required
            if int(summary.get(comp, {}).get("evidence_count", 0) or 0)
            >= MIN_QUESTIONS_PER_COMPETENCY
            and float(
                summary.get(comp, {}).get("gap")
                if summary.get(comp, {}).get("gap") is not None
                else 1.0
            )
            <= SUFFICIENCY_GAP_THRESHOLD
        )
        coverage = covered / len(required) if required else 0.0

    return compute_canonical_score(competency_average, hypothesis_confidence, coverage)


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

    # Fix for coverage: Allow finishing if enough high-priority competencies are covered
    # even if total coverage_ratio is lower, as high-priority competencies are most critical
    # Use predefined high-priority IDs as proxy for priority checking
    def is_high_priority(comp_id: str) -> bool:
        return comp_id in _HIGH_PRIORITY_IDS or comp_id in _HIGH_MIDS

    high_priority_covered = sum(
        1 for cid, d in comp_details.items() if d.get("covered") and is_high_priority(cid)
    )
    if filtered_required:
        high_priority_count = sum(1 for cid in filtered_required if is_high_priority(cid))
        high_priority_ratio = high_priority_covered / high_priority_count if high_priority_count > 0 else 0
    else:
        high_priority_ratio = coverage_ratio

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

    # hypothesis_confidence in 0..1 — diluted by untested hypotheses so an
    # unvalidated profile can never carry a full confirmation bonus.
    untested = hypothesis_statuses.get("untested", 0)
    hypothesis_confidence = resolved_hypothesis_confidence(
        confirmed,
        refuted,
        untested,
        avg_confidence if avg_confidence > 0 else 0.5,
    )

    # coverage_ratio already computed (0..1)

    # Final scoring: the canonical composite (single source of truth — see
    # ``compute_canonical_score``). Scales hypothesis confidence and coverage
    # to 0..10 before weighting so the result is on the 0..10 range.
    final_score = compute_canonical_score(
        competency_average_score=competency_average_score,
        hypothesis_confidence=hypothesis_confidence,
        coverage_ratio=coverage_ratio,
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

    # Difficulty cap: un-stress-tested evidence is discounted. A session stuck
    # at difficulty 1-2 can never recommend hire — the decision engine applies
    # the same restriction via its difficulty credit, so recommendation and
    # decision cannot contradict each other.
    if difficulty_reached is not None:
        cap = _DIFFICULTY_VERDICT_CAPS.get(int(difficulty_reached))
        if cap and _DIFFICULTY_VERDICT_ORDER.index(verdict) > _DIFFICULTY_VERDICT_ORDER.index(cap):
            verdict = cap

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


def _required_gaps_ok(
    competency_summary: dict,
    required_competencies: list[str],
    hypotheses: list,
) -> bool:
    """True when every required competency has its minimum evidence, no gap,
    and none of its hypotheses was never explored (``untested``).

    An interview must not end while required competencies are still starved of
    evidence or required hypotheses were never tested — the only escape from
    this gate is the hard question cap in :func:`decide_next_action`.
    """
    for comp in required_competencies:
        summary = competency_summary.get(comp, {}) or {}
        count = int(summary.get("evidence_count", 0) or 0)
        gap = summary.get("gap")
        gap = float(gap) if gap is not None else 1.0
        if count < MIN_QUESTIONS_PER_COMPETENCY or gap > SUFFICIENCY_GAP_THRESHOLD:
            return False
    if any(
        h.get("status") == "untested"
        for h in (hypotheses or [])
        if h.get("competency") in required_competencies
    ):
        return False
    return True


def _finish_gates_ok(
    evidence_sufficiency: dict,
    difficulty_reached: int | None,
    difficulty_floor: int | None,
) -> bool:
    """Role-profile finish gates: most of the required set covered AND the
    interview pushed the candidate past the role's difficulty floor. Weak
    candidates burn the question budget instead of ending with a half-tested
    profile — the hard ``max_questions`` cap is the only escape."""

    if (evidence_sufficiency.get("coverage_ratio") or 0.0) < FINISH_MIN_COVERAGE:
        return False
    if difficulty_floor is not None and (difficulty_reached or 0) < difficulty_floor:
        return False
    return True


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
    difficulty_floor: int | None = None,
) -> str:
    max_questions = 14  # AURA cap — the only escape from evidence gating

    if evidence_sufficiency.get("is_sufficient"):
        # Fix 11: hard floor — never finish before enough questions were
        # answered to justify a decision, whatever the signals say.
        # Fix 12: even sufficient evidence must not finish while a required
        # competency still has a gap or a required hypothesis was never
        # tested — keep probing until those are resolved (or the cap hits).
        # V5: senior profiles must also reach both the coverage breadth and
        # the role's difficulty floor before the committee can rule.
        if (
            question_number >= MIN_QUESTIONS_BEFORE_FINISH
            and _required_gaps_ok(competency_summary, required_competencies, hypotheses)
            and _finish_gates_ok(evidence_sufficiency, difficulty_reached, difficulty_floor)
        ):
            return "finish"
        if question_number >= max_questions:
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
        and _finish_gates_ok(evidence_sufficiency, difficulty_reached, difficulty_floor)
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
        # All hypotheses settled. Finish only when the required competencies
        # are actually covered — otherwise rotate to probe the uncovered ones
        # (each rotation seeds a fresh hypothesis for the next competency).
        coverage_ratio = evidence_sufficiency.get("coverage_ratio", 0.0)
        if (
            question_number >= MIN_QUESTIONS_BEFORE_FINISH
            and coverage_ratio >= COVERAGE_THRESHOLD
            and _required_gaps_ok(competency_summary, required_competencies, hypotheses)
            and _finish_gates_ok(evidence_sufficiency, difficulty_reached, difficulty_floor)
        ):
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

    if question_number >= max_questions:
        return "finish"

    # Top difficulty + decent coverage + at least 5 questions = pushed far
    # enough to decide — but only when the required competencies are actually
    # covered and no required hypothesis was never tested. High difficulty is
    # no excuse for ending with evidence gaps.
    coverage_ratio = evidence_sufficiency.get("coverage_ratio", 0.0)

    # Fix for coverage: Allow finishing with partial coverage if:
    # 1. High priority coverage is good (60% of HIGH/MEDIUM competencies)
    # 2. OR high difficulty reached with 50% total coverage
    details = evidence_sufficiency.get("details") or {}
    high_priority_items = [
        d for c, d in details.items()
        if c in _HIGH_PRIORITY_IDS or c in _HIGH_MIDS
    ]
    high_priority_ratio = (
        (sum(1 for d in high_priority_items if d.get("covered")) / len(high_priority_items))
        if high_priority_items
        else 0.0
    )
    high_priority_coverage_ok = high_priority_ratio >= 0.6  # 60% of high-priority covered
    partial_coverage_ok = coverage_ratio >= 0.5 and question_number >= 5

    if (
        difficulty_reached
        and difficulty_reached >= HIGH_DIFFICULTY_FINISH
        and (high_priority_coverage_ok or partial_coverage_ok)
        and question_number >= 5
        and _required_gaps_ok(competency_summary, required_competencies, hypotheses)
        and _finish_gates_ok(evidence_sufficiency, difficulty_reached, difficulty_floor)
    ):
        return "finish"

    return "probe"
