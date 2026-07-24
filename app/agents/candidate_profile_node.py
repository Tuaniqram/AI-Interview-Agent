import json
import logging
from uuid import UUID

from app.graph.interview_state import InterviewState
from app.database.session import get_session_factory
from app.models.db import CandidateProfile

logger = logging.getLogger(__name__)

_UPDATE_THROTTLE = 3
_answer_counter: dict[str, int] = {}


async def candidate_profile_node(state: InterviewState) -> InterviewState:
    session_id = state.get("session_id", "")
    candidate_id = state.get("candidate_id", "")

    existing = state.get("candidate_profile")
    if existing:
        profile = dict(existing)
    else:
        profile = await _load_profile(candidate_id)
        if not profile:
            profile = _empty_profile(candidate_id)

    new_evidence = state.get("extracted_evidence", [])
    if new_evidence:
        profile = _update_profile(profile, new_evidence)

    count = _answer_counter.get(session_id, 0) + 1
    _answer_counter[session_id] = count
    if count % _UPDATE_THROTTLE == 0 and candidate_id:
        await _save_profile(candidate_id, profile)
        logger.info(f"Saved candidate profile for {candidate_id} (answer #{count})")

    return {
        **state,
        "candidate_profile": profile,
    }


async def _load_profile(candidate_id: str) -> dict | None:
    if not candidate_id:
        return None
    try:
        async with get_session_factory()() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(CandidateProfile).where(CandidateProfile.id == UUID(candidate_id))
            )
            instance = result.scalar_one_or_none()
            if instance and instance.profile_data:
                return dict(instance.profile_data)
    except Exception as e:
        logger.warning(f"Failed to load candidate profile: {e}")
    return None


async def _save_profile(candidate_id: str, profile: dict) -> None:
    try:
        async with get_session_factory()() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(CandidateProfile).where(CandidateProfile.id == UUID(candidate_id))
            )
            instance = result.scalar_one_or_none()
            if instance:
                instance.profile_data = profile
                await session.commit()
    except Exception as e:
        logger.warning(f"Failed to save candidate profile: {e}")


def _empty_profile(candidate_id: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "technical": {},
        "communication": {},
        "behavioral": {},
        "leadership": {},
        "architecture": {},
        "debugging": {},
        "ownership": {},
        "learning": {},
        "confidence_trait": {},
        "strengths": [],
        "weaknesses": [],
        "risk_flags": [],
        "contradictions": [],
        "evidence_summary": {},
        "session_count": 0,
        "last_updated": None,
    }


def _update_profile(profile: dict, evidence_list: list[dict]) -> dict:
    profile = dict(profile)
    strengths_set = set(profile.get("strengths", []))
    weaknesses_set = set(profile.get("weaknesses", []))

    for ev in evidence_list:
        comp = ev.get("competency", "")
        dim = ev.get("dimension", "")
        score = ev.get("score", 0.0)
        confidence = ev.get("confidence", 1.0)

        key = _map_to_profile_key(dim, comp)
        if key:
            current = profile.get(key, {})
            scores = current.get("scores", [])
            scores.append(score)
            avg = sum(scores) / len(scores)
            profile[key] = {
                "scores": scores,
                "average_score": round(avg, 2),
                "latest_score": score,
                "confidence": confidence,
                "count": len(scores),
            }

        summary_key = comp if comp else dim
        summary = profile.get("evidence_summary", {})
        comp_summary = summary.get(summary_key, {"evidence_count": 0, "scores": []})
        comp_summary["evidence_count"] += 1
        comp_summary["scores"].append(score)
        comp_summary["average_score"] = round(
            sum(comp_summary["scores"]) / comp_summary["evidence_count"], 2
        )
        comp_summary["latest_score"] = score
        comp_summary["latest_evidence"] = ev.get("evidence_text", "")
        summary[summary_key] = comp_summary
        profile["evidence_summary"] = summary

        ev_strengths = ev.get("strengths", [])
        for s in ev_strengths:
            if s and isinstance(s, str):
                strengths_set.add(s)

        ev_weaknesses = ev.get("weaknesses", [])
        for w in ev_weaknesses:
            if w and isinstance(w, str):
                weaknesses_set.add(w)

    profile["strengths"] = sorted(strengths_set, key=str.lower)
    profile["weaknesses"] = sorted(weaknesses_set, key=str.lower)
    profile["session_count"] = profile.get("session_count", 0) + (1 if evidence_list else 0)

    return profile


def _map_to_profile_key(dimension: str, competency: str) -> str | None:
    dimension_key_map = {
        "technical": "technical",
        "communication": "communication",
        "behavioral": "behavioral",
        "reasoning": "architecture",
        "confidence": "confidence_trait",
    }
    if dimension in dimension_key_map:
        return dimension_key_map[dimension]
    competency_key_map = {
        "behav_leadership": "leadership",
        "behav_adaptability": "learning",
        "exp_project_depth": "ownership",
        "cog_problem_solving": "debugging",
    }
    return competency_key_map.get(competency, None)
