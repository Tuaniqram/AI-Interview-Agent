import json
import logging
from uuid import uuid4
from datetime import datetime, timezone

from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)

_DIMENSION_KEYS = {"technical", "communication", "reasoning", "behavioral", "confidence", "completeness"}


async def unified_evaluator_node(state: InterviewState) -> InterviewState:
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    question = state.get("current_question", "")
    answer = state.get("candidate_answer", "")
    job_role = state.get("job_role", "Unknown")
    difficulty = state.get("difficulty_level", 1)
    persona = state.get("persona", "friendly")
    evaluator_mode = state.get("evaluator_mode", "unified")
    style = state.get("interview_style", {})
    weights = style.get("evaluator_weights", {})
    competency = state.get("question_objective", {}).get("target_competency", "")
    domain_label = state.get("domain_label", "Technical Knowledge")

    if evaluator_mode == "parallel":
        return await _parallel_evaluator(
            state, question, answer, job_role, difficulty, persona, competency, domain_label
        )

    return await _unified_evaluator(
        state, question, answer, job_role, difficulty, persona, competency, weights, domain_label
    )


async def _unified_evaluator(
    state: InterviewState,
    question: str,
    answer: str,
    job_role: str,
    difficulty: int,
    persona: str,
    competency: str,
    weights: dict,
    domain_label: str,
) -> InterviewState:
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    if not answer or not answer.strip():
        return _empty_evaluation(state, "No answer provided")

    try:
        llm_service = get_llm_service()

        prompt = load_prompt(
            "evaluation",
            "unified_evaluator.md",
            question=question,
            answer=answer[:3000] if answer else "",
            job_role=job_role,
            difficulty=str(difficulty),
            persona=persona,
            competency=competency or "General",
            domain_label=domain_label,
        )

        response = await llm_service.invoke(
            prompt=prompt,
            temperature=0.3,
            max_tokens=1500,
        )

        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        data = json.loads(response)
    except Exception as e:
        logger.warning(f"Unified evaluator LLM failed: {e}")
        return _empty_evaluation(state, f"Evaluation error: {str(e)}")

    evaluation = {}
    for key in _DIMENSION_KEYS:
        dim_data = data.get(key, {})
        if isinstance(dim_data, dict):
            evaluation[key] = {
                "score": dim_data.get("score"),
                "evidence": dim_data.get("evidence", ""),
                "confidence": dim_data.get("confidence", 0.5),
                "strengths": dim_data.get("strengths", []),
                "weaknesses": dim_data.get("weaknesses", []),
            }
        else:
            evaluation[key] = None

    observations = data.get("observations", {})
    if not isinstance(observations, dict):
        observations = {}

    composite = data.get("composite_score")
    if composite is None:
        scores = [
            evaluation[d].get("score", 0) or 0
            for d in evaluation if evaluation[d] and evaluation[d].get("score") is not None
        ]
        composite = round(sum(scores) / len(scores), 2) if scores else 0.0
    else:
        composite = round(float(composite), 2)

    weighted = _compute_weighted(evaluation, weights)

    obs_list = []
    for obs_key in ("verbosity", "hedging", "certainty_shift", "sentiment_shift", "response_latency_estimate", "notable_patterns"):
        val = observations.get(obs_key)
        if val is not None:
            obs_list.append({
                "type": obs_key,
                "value": val if isinstance(val, (int, float)) else 0.5,
                "evidence": str(val) if not isinstance(val, (int, float)) else "",
            })

    return {
        **state,
        "unified_evaluation": evaluation,
        "evaluation_score": composite,
        "observations": obs_list,
        "observation_trends": observations,
    }


async def _parallel_evaluator(
    state: InterviewState,
    question: str,
    answer: str,
    job_role: str,
    difficulty: int,
    persona: str,
    competency: str,
    domain_label: str,
) -> InterviewState:
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    if not answer or not answer.strip():
        return _empty_evaluation(state, "No answer provided")

    try:
        llm_service = get_llm_service()

        async def eval_dimension(dim: str) -> tuple[str, dict]:
            try:
                prompt = load_prompt(
                    "evaluation",
                    f"{dim}_evaluator.md",
                    question=question,
                    answer=answer[:3000] if answer else "",
                    job_role=job_role,
                    difficulty=str(difficulty),
                    persona=persona,
                    competency=competency or "General",
                    domain_label=domain_label,
                )
                resp = await llm_service.invoke(prompt=prompt, temperature=0.3, max_tokens=500)
                resp = resp.strip()
                if resp.startswith("```json"):
                    resp = resp[7:]
                if resp.startswith("```"):
                    resp = resp[3:]
                if resp.endswith("```"):
                    resp = resp[:-3]
                resp = resp.strip()
                return dim, json.loads(resp)
            except Exception as e:
                logger.warning(f"Parallel evaluator {dim} failed: {e}")
                return dim, {"score": None, "evidence": str(e), "confidence": 0.0}

        import asyncio
        results = await asyncio.gather(*[eval_dimension(d) for d in _DIMENSION_KEYS])

        evaluation = {}
        obs_list = []
        for dim, data in results:
            evaluation[dim] = {
                "score": data.get("score"),
                "evidence": data.get("evidence", ""),
                "confidence": data.get("confidence", 0.5),
                "strengths": data.get("strengths", []),
                "weaknesses": data.get("weaknesses", []),
            }

        scores = [
            evaluation[d].get("score", 0) or 0
            for d in evaluation if evaluation[d].get("score") is not None
        ]
        composite = round(sum(scores) / len(scores), 2) if scores else 0.0

        style = state.get("interview_style", {})
        weights = style.get("evaluator_weights", {})
        weighted = _compute_weighted(evaluation, weights)

        return {
            **state,
            "unified_evaluation": evaluation,
            "evaluation_score": weighted or composite,
            "observations": obs_list,
            "observation_trends": {},
        }
    except Exception as e:
        logger.error(f"Parallel evaluator failed: {e}")
        return _empty_evaluation(state, f"Evaluation error: {str(e)}")


def _compute_weighted(evaluation: dict, weights: dict) -> float | None:
    total_weight = 0.0
    weighted_sum = 0.0
    for dim, weight in weights.items():
        dim_data = evaluation.get(dim)
        if dim_data and dim_data.get("score") is not None:
            weighted_sum += dim_data["score"] * weight
            total_weight += weight
    if total_weight > 0:
        return round(weighted_sum / total_weight, 2)
    return None


def _empty_evaluation(state: InterviewState, reason: str) -> InterviewState:
    empty = {
        dim: {"score": None, "evidence": reason, "confidence": 0.0, "strengths": [], "weaknesses": []}
        for dim in _DIMENSION_KEYS
    }
    return {
        **state,
        "unified_evaluation": empty,
        "evaluation_score": None,
        "observations": [],
        "observation_trends": {},
    }
