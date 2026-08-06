import json
import logging
from uuid import uuid4
from datetime import datetime, timezone

from app.core.interview_state import InterviewState
from app.agents.generation.question_memory import (
    avoid_topics_summary,
    recent_memory,
)
from app.agents.generation.question_similarity_guard import QuestionSimilarityGuard

logger = logging.getLogger(__name__)

MAX_FOLLOWUPS_PER_COMPETENCY = 3
# One retry only: the cheap LLM tier repeats the rejected topic even when
# told about it, so a second retry costs another 5-20s (429 backoff) for the
# same outcome. The deterministic fallback guarantees a fresh question.
MAX_DUPLICATE_RETRIES = 1

# Probe-mode → interviewer mode (Fix 4 depth strategy).
_MODE_BY_PROBE_MODE = {
    "explore_new_competency": "EXPLORER",
    "deep_probe": "PROBER",
    "challenge_candidate": "CHALLENGER",
    "verify_claim": "VERIFIER",
    "finish_competency": "CLOSER",
}

_MODE_DESCRIPTIONS = {
    "EXPLORER": "First probe of an area: open-ended, ask for a concrete project or example",
    "PROBER": "Follow up on a strong answer: drill into specifics (data, invalidation, failure behavior)",
    "CHALLENGER": "Stress-test a senior candidate: trade-offs, alternatives, edge cases",
    "VERIFIER": "Verify a claim: ask how it was measured or demonstrated",
    "CLOSER": "Wrap up: confirm overall picture with one final question",
}


def _resolve_interview_mode(state: InterviewState) -> str:
    """The interviewer depth mode for the next question (Fix 2/4).

    Primary source is the director's ``probe_mode``; falls back to
    difficulty/evidence heuristics when the director did not run.
    """
    director = state.get("director") or {}
    probe_mode = director.get("probe_mode")
    if probe_mode in _MODE_BY_PROBE_MODE:
        return _MODE_BY_PROBE_MODE[probe_mode]

    difficulty = int(state.get("difficulty_level", 1) or 1)
    summary = state.get("competency_summary") or {}
    target = state.get("hypothesis_target") or {}
    competency = target.get("competency", "")
    collected = int(summary.get(competency, {}).get("evidence_count", 0) or 0)
    if difficulty >= 4:
        return "CHALLENGER"
    if collected > 0:
        return "PROBER"
    return "EXPLORER"


async def question_generator_node(state: InterviewState) -> InterviewState:
    strategy = state.get("interview_strategy", {})
    hypothesis_target = state.get("hypothesis_target")
    competency_summary = state.get("competency_summary", {})
    current_question = state.get("current_question", "")
    question_number = state.get("question_number", 0)
    persona = state.get("persona", "friendly")
    job_role = state.get("job_role", "Unknown")
    previous_questions = state.get("questions_asked", [])
    candidate_profile = state.get("candidate_profile", {})
    last_question = (
        str(previous_questions[-1].get("text", "")).strip()
        if previous_questions and isinstance(previous_questions[-1], dict)
        else ""
    )

    difficulty = state.get("difficulty_level", 1)
    interview_mode = _resolve_interview_mode(state)
    memory = recent_memory(previous_questions)

    target_competency = ""
    target_hypothesis = {}

    if hypothesis_target:
        target_competency = hypothesis_target.get("competency", "")
        target_hypothesis = hypothesis_target

    # Fix 11: a target-less question misattributes its evidence (dim_* records)
    # and drifts the interview — fall back to the planner's competency so the
    # objective is always populated.
    if not target_competency:
        target_competency = state.get("planned_competency") or ""
    # Fix 12: ``planned_competency`` may not survive the brain round-trip (the
    # planner commits ``next_competency`` on the brain) — without this second
    # fallback the objective degraded to "general" and evidence never landed
    # on the competency the question targeted.
    if not target_competency:
        next_c = state.get("next_competency")
        if isinstance(next_c, dict):
            target_competency = next_c.get("id") or ""
        elif next_c:
            target_competency = str(next_c)
    if target_competency:
        target_hypothesis = target_hypothesis or {
            "id": "",
            "competency": target_competency,
        }

    competency_info = ""
    if target_competency and target_competency in competency_summary:
        cs = competency_summary[target_competency]
        competency_info = (
            f"Current average: {cs.get('average_score', 'N/A')}/10, "
            f"evidence count: {cs.get('evidence_count', 0)}, "
            f"gap: {cs.get('gap', 1.0)}"
        )

    if strategy and isinstance(strategy, dict):
        approach = strategy.get("question_strategy", strategy.get("approach", ""))
    else:
        approach = ""

    if hypothesis_target and hypothesis_target.get("statement"):
        hypothesis_text = hypothesis_target["statement"]
    else:
        hypothesis_text = ""

    last_answer = _last_user_message(state.get("conversation_history", []))
    company_context = _company_context(state, interview_mode)
    avoid_topics = avoid_topics_summary(memory)

    async def _emit(attempt: int = 0, last_rejected: str = "") -> tuple[dict | None, str]:
        """Generate one question, bumping the deterministic template slot on
        retries so a rejected duplicate is not regenerated verbatim."""
        if persona == "conductor":
            conversation_turn = await _generate_conductor_turn(
                state=state,
                phase=state.get("current_phase", "technical"),
                target_competency=target_competency or "general",
                job_role=job_role,
                difficulty=difficulty,
                hypothesis_text=hypothesis_text,
                competency_info=competency_info,
                last_answer=last_answer,
                company_context=company_context,
                interview_mode=interview_mode,
                avoid_topics=avoid_topics,
                last_rejected=last_rejected,
                last_question=last_question,
            )
            return conversation_turn, conversation_turn["question"]
        try:
            question_text = await _generate_llm_question(
                phase=state.get("current_phase", "technical"),
                target_competency=target_competency or "general",
                job_role=job_role,
                difficulty=difficulty,
                approach=approach,
                hypothesis_text=hypothesis_text,
                competency_info=competency_info,
                candidate_profile=candidate_profile,
                persona=persona,
                followup_number=_count_competency_questions(previous_questions, target_competency),
                question_number=question_number,
                total_questions=state.get("total_questions", 10),
                conversation_history=state.get("conversation_history", []),
                company_context=company_context,
                interview_mode=interview_mode,
                avoid_topics=avoid_topics,
                last_rejected=last_rejected,
                last_question=last_question,
            )
        except Exception as e:
            logger.warning(f"LLM question generation failed ({e}), falling back to deterministic")
            question_text = _generate_deterministic_question(
                target_competency=target_competency or "general",
                job_role=job_role,
                difficulty=difficulty,
                approach=approach,
                hypothesis_text=hypothesis_text,
                competency_info=competency_info,
                candidate_profile=candidate_profile,
                persona=persona,
                followup_number=_count_competency_questions(previous_questions, target_competency),
                interview_mode=interview_mode,
                attempt_offset=attempt,
            )
        return None, question_text

    guard = QuestionSimilarityGuard()
    # Mode-aware comparison: a fresh EXPLORER question (new competency) must
    # pivot topics from EVERYTHING already asked — compare against all prior
    # questions with a stricter bar. A PROBER/CHALLENGER follow-up may
    # legitimately go deeper on the current competency, so it is only compared
    # against that competency's own prior questions.
    if interview_mode == "EXPLORER":
        guard.similarity_threshold = 0.78
        guard_memory = [
            str(q.get("text", "")).strip()
            for q in previous_questions
            if str(q.get("text", "")).strip()
        ]
    else:
        guard.similarity_threshold = 0.85
        guard_memory = [
            str(q.get("text", "")).strip()
            for q in previous_questions
            if q.get("competency") == target_competency and str(q.get("text", "")).strip()
        ]

    conversation_turn = None
    question_text = ""
    rejected_texts: list[str] = []
    for attempt in range(MAX_DUPLICATE_RETRIES + 1):
        conversation_turn, question_text = await _emit(attempt, last_rejected=rejected_texts[-1] if rejected_texts else "")
        duplicate, detail = guard.is_duplicate(question_text, guard_memory)
        if not duplicate:
            break
        logger.info(
            f"Rejected duplicate question (attempt {attempt + 1}): "
            f"{detail.get('kind')} against {detail.get('against', '')[:80]!r} "
            f"(score={guard.similarity_score}, embedding={guard.used_embedding})"
        )
        rejected_texts.append(question_text)
        question_text = ""

    if not question_text:
        # Every attempt was rejected/errored — skip the templates that were
        # already tried (an offset can wrap back onto a rejected slot) and
        # re-check the fallback against the guard before emitting it.
        question_text = ""
        for offset in range(MAX_DUPLICATE_RETRIES + 1):
            candidate = _generate_deterministic_question(
                target_competency=target_competency or "general",
                job_role=job_role,
                difficulty=difficulty,
                approach=approach,
                hypothesis_text=hypothesis_text,
                competency_info=competency_info,
                candidate_profile=candidate_profile,
                persona=persona,
                followup_number=_count_competency_questions(previous_questions, target_competency),
                interview_mode="EXPLORER",
                attempt_offset=offset,
            )
            if candidate in rejected_texts:
                continue
            is_dup, _ = guard.is_duplicate(candidate, guard_memory)
            if not is_dup:
                question_text = candidate
                break
        if not question_text:
            question_text = _fallback_question(target_competency or "general", job_role, difficulty)
        conversation_turn = None

    question_id = str(uuid4())

    probe_mode = next(
        (pm for pm, mode in _MODE_BY_PROBE_MODE.items() if mode == interview_mode),
        "exploratory",
    )
    question_objective = {
        "question_id": question_id,
        "target_competency": target_competency,
        "target_hypothesis_id": hypothesis_target.get("id", "") if hypothesis_target else "",
        "difficulty": difficulty,
        "type": probe_mode,
        "mode": interview_mode,
    }

    questions_asked = list(previous_questions)
    questions_asked.append({
        "id": question_id,
        "text": question_text,
        "competency": target_competency,
        "difficulty": difficulty,
        "mode": interview_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        **state,
        "current_question": question_text,
        "conversation_turn": conversation_turn,
        "question_objective": question_objective,
        "questions_asked": questions_asked,
        "question_number": question_number + 1,
        "interview_mode": interview_mode,
    }


def _last_user_message(conversation_history: list) -> str:
    for h in reversed(conversation_history or []):
        if h.get("role") == "user" and h.get("content"):
            return h["content"][:600]
    return ""


def _company_context(state: dict, interview_mode: str = "") -> str:
    """Summarize the V5 company brain for the question prompt (best-effort).

    Mode-aware: only the first question of a competency (explore_new_competency)
    is grounded in company context; follow-up probes (deep_probe / challenge /
    verify) are about counter-evidence and get "N/A" so cheap-tier prompts stay
    minimal and the interviewer stops repeating company framing.
    """
    if interview_mode and interview_mode != "EXPLORER":
        return "N/A"
    cb = state.get("company_brain") or {}
    if not cb:
        return "N/A"
    parts = []
    vision = cb.get("company_vision") or cb.get("mission") or ""
    if isinstance(vision, str) and vision.strip():
        parts.append(vision.strip()[:300])
    tech = cb.get("technical_stack") or cb.get("tech_stack") or []
    if isinstance(tech, list) and tech:
        parts.append(f"Technical stack: {', '.join(str(t) for t in tech[:8])}")
    culture = cb.get("culture") or []
    if isinstance(culture, list) and culture:
        parts.append(f"Culture: {', '.join(str(c) for c in culture[:6])}")
    signals = cb.get("success_signals") or []
    if isinstance(signals, list) and signals:
        parts.append(f"Success signals: {', '.join(str(s) for s in signals[:4])}")
    return " | ".join(parts) if parts else "N/A"


def _question_prompt_vars(
    *,
    job_role: str,
    target_competency: str,
    phase: str,
    difficulty: int,
    persona: str,
    hypothesis: str,
    competency_info: str,
    approach: str,
    followup_number: int,
    question_number: int,
    total_questions: int,
    conversation_history: list,
    candidate_profile: dict,
    department_context: str = "N/A",
    company_context: str = "N/A",
    interview_mode: str = "EXPLORER",
    avoid_topics: str = "None",
    last_rejected: str = "",
    last_question: str = "",
) -> dict:
    """Single source of truth for the question_generation prompt's variables."""
    history_lines = []
    for h in (conversation_history or [])[-6:]:
        role = h.get("role", "")
        content = h.get("content", "")
        if content:
            history_lines.append(f"{role}: {content[:500]}")
    history_summary = "\n".join(history_lines) if history_lines else "(no previous conversation)"
    profile_json = json.dumps(candidate_profile) if candidate_profile else "{}"
    return {
        "job_role": job_role or "Unknown",
        "target_competency": target_competency or "general",
        "phase": phase,
        "difficulty": difficulty,
        "difficulty_level": difficulty,
        "persona": persona or "friendly",
        "hypothesis": hypothesis or "No specific hypothesis yet",
        "competency_info": competency_info or "No evidence gathered yet",
        "approach": approach or "Explore the competency",
        "followup_number": followup_number,
        "department_context": department_context,
        "candidate_profile": profile_json[:2000] or "N/A",
        "question_number": question_number + 1,
        "total_questions": total_questions,
        "conversation_history": history_summary,
        "company_context": company_context,
        "interview_mode": interview_mode,
        "avoid_topics": avoid_topics or "None",
        "last_rejected": last_rejected or "None",
        "last_question": last_question or "None",
    }


async def _generate_conductor_turn(
    state: InterviewState,
    phase: str,
    target_competency: str,
    job_role: str,
    difficulty: int,
    hypothesis_text: str,
    competency_info: str,
    last_answer: str,
    company_context: str = "N/A",
    interview_mode: str = "EXPLORER",
    avoid_topics: str = "None",
    last_rejected: str = "",
    last_question: str = "",
) -> dict:
    """One LLM call producing {acknowledgement, bridge, question} (AURA conductor)."""
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    try:
        llm_service = get_llm_service()

        strategy = state.get("interview_strategy") or {}
        if isinstance(strategy, dict):
            approach = strategy.get("question_strategy", strategy.get("approach", ""))
        else:
            approach = ""

        prompt = load_prompt(
            "interview",
            "question_generation.md",
            **_question_prompt_vars(
                job_role=job_role,
                target_competency=target_competency,
                phase=phase,
                difficulty=difficulty,
                persona="conductor",
                hypothesis=hypothesis_text,
                competency_info=competency_info,
                approach=approach,
                followup_number=_count_competency_questions(
                    state.get("questions_asked", []), target_competency
                ),
                question_number=state.get("question_number", 0),
                total_questions=state.get("total_questions", 10),
                conversation_history=state.get("conversation_history", []),
                candidate_profile=state.get("candidate_profile", {}),
                company_context=company_context,
                interview_mode=interview_mode,
                avoid_topics=avoid_topics,
                last_rejected=last_rejected,
                last_question=last_question,
            ),
        )

        response = await llm_service.invoke(prompt=prompt, temperature=0.7, max_tokens=400, tier="cheap")
        return _parse_conductor_turn(response)
    except Exception as e:
        logger.warning(f"Conductor turn generation failed ({e}), using deterministic fallback")
        return _generate_deterministic_conductor_turn(
            target_competency=target_competency,
            job_role=job_role,
            difficulty=difficulty,
            hypothesis_text=hypothesis_text,
            competency_info=competency_info,
            last_answer=last_answer,
            interview_mode=interview_mode,
            attempt_offset=0,
        )


def _parse_conductor_turn(response: str) -> dict:
    from app.intelligence._helpers import parse_json

    data = parse_json(response)
    question = str(data.get("question", "")).strip()
    if not question:
        raise ValueError("Conductor turn missing question")
    return {
        "acknowledgement": str(data.get("acknowledgement", "")).strip(),
        "bridge": str(data.get("bridge", "")).strip(),
        "question": question,
    }


def _generate_deterministic_conductor_turn(
    target_competency: str,
    job_role: str,
    difficulty: int,
    hypothesis_text: str,
    competency_info: str,
    last_answer: str,
    interview_mode: str = "EXPLORER",
    attempt_offset: int = 0,
) -> dict:
    question = _generate_deterministic_question(
        target_competency=target_competency,
        job_role=job_role,
        difficulty=difficulty,
        approach="",
        hypothesis_text=hypothesis_text,
        competency_info=competency_info,
        candidate_profile={},
        persona="conductor",
        followup_number=0,
        interview_mode=interview_mode,
        attempt_offset=attempt_offset,
    )

    if last_answer:
        acknowledgement = "Got it. Let me dig into that."
    else:
        acknowledgement = "Let's get started."

    return {
        "acknowledgement": acknowledgement,
        "bridge": f"Now, about {target_competency.replace('_', ' ')}...",
        "question": question,
    }


async def _generate_llm_question(
    phase: str,
    target_competency: str,
    job_role: str,
    difficulty: int,
    approach: str,
    hypothesis_text: str,
    competency_info: str,
    candidate_profile: dict,
    persona: str,
    followup_number: int,
    question_number: int,
    total_questions: int,
    conversation_history: list,
    company_context: str = "N/A",
    interview_mode: str = "EXPLORER",
    avoid_topics: str = "None",
    last_rejected: str = "",
    last_question: str = "",
) -> str:
    """Generate the next question with the LLM using the question_generation prompt."""
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    llm_service = get_llm_service()

    prompt = load_prompt(
        "interview",
        "question_generation.md",
        **_question_prompt_vars(
            job_role=job_role,
            target_competency=target_competency,
            phase=phase,
            difficulty=difficulty,
            persona=persona,
            hypothesis=hypothesis_text,
            competency_info=competency_info,
            approach=approach,
            followup_number=followup_number,
            question_number=question_number,
            total_questions=total_questions,
            conversation_history=conversation_history,
            candidate_profile=candidate_profile,
            department_context="N/A",
            company_context=company_context,
            interview_mode=interview_mode,
            avoid_topics=avoid_topics,
            last_rejected=last_rejected,
            last_question=last_question,
        ),
    )

    response = await llm_service.invoke(prompt=prompt, temperature=0.8, max_tokens=200, tier="cheap")
    question = (response or "").strip()
    if question.startswith("Question:"):
        question = question[len("Question:"):].strip()
    if not question:
        raise ValueError("LLM returned an empty question")
    return question


def _generate_deterministic_question(
    target_competency: str,
    job_role: str,
    difficulty: int,
    approach: str,
    hypothesis_text: str,
    competency_info: str,
    candidate_profile: dict,
    persona: str,
    followup_number: int,
    interview_mode: str = "EXPLORER",
    attempt_offset: int = 0,
) -> str:
    """Deterministic fallback question, shaped by the interview depth mode.

    ``attempt_offset`` shifts the template slot on duplicate retries so a
    rejected question is never regenerated verbatim.
    """
    if hypothesis_text:
        direction = "positive" if "strong" in hypothesis_text.lower() else "negative"
        if direction == "positive" and followup_number > 0:
            return (
                f"You mentioned you have strength in this area. Can you walk me through a specific "
                f"challenging project where you applied advanced {target_competency.replace('_', ' ')} concepts? "
                f"What was the hardest problem you had to solve?"
            )
        elif direction == "positive":
            return (
                f"Based on your background, I'd like to explore your {target_competency.replace('_', ' ')} skills. "
                f"Can you describe a complex problem you solved in this area? What was your approach and why?"
            )
        else:
            return (
                f"I'd like to understand your experience with {target_competency.replace('_', ' ')}. "
                f"Tell me about a time when you faced a significant challenge in this area. "
                f"How did you approach it and what was the outcome?"
            )

    templates = _get_template_for_competency(target_competency, job_role, difficulty)
    if templates:
        idx = min(followup_number + attempt_offset, len(templates) - 1) if followup_number + attempt_offset < len(templates) else 0
        question = templates[idx]
        return _apply_mode_flavor(question, interview_mode, target_competency)

    question = _fallback_question(target_competency, job_role, difficulty)
    return _apply_mode_flavor(question, interview_mode, target_competency)


def _apply_mode_flavor(question: str, interview_mode: str, target_competency: str) -> str:
    """Attach the interviewer depth strategy to a deterministic question."""
    comp_name = target_competency.replace("_", " ")
    if interview_mode == "CHALLENGER":
        return (
            f"{question} Now, challenge yourself: what were the trade-offs, what would you do "
            f"differently at twice the scale, and how would you defend that choice?"
        )
    if interview_mode == "VERIFIER":
        return f"{question} How was that measured or demonstrated — what concrete evidence did you see?"
    if interview_mode == "PROBER":
        return f"{question} Give me the specifics: what data or details made you certain it was the right call?"
    if interview_mode == "CLOSER":
        return (
            f"{question} And as a final question on {comp_name}: what would you do first "
            f"if you owned this area tomorrow?"
        )
    return question


def _get_template_for_competency(competency: str, job_role: str, difficulty: int) -> list[str]:
    templates = {
        "tech_core": [
            f"What core technical skills in {job_role} do you consider your strongest? Provide an example.",
            f"How do you stay current with technology trends relevant to {job_role}?",
            f"Describe a complex technical decision you made in your last {job_role} role and its impact.",
        ],
        "system_design": [
            f"Design a scalable system for {job_role}. Walk me through your architectural decisions.",
            f"How do you approach trade-offs when designing distributed systems?",
            f"Describe a system you built or improved. What were the key design goals?",
        ],
        "problem_solving": [
            f"Describe a difficult problem you solved in your last {job_role} position.",
            f"How do you approach debugging a complex production issue?",
            f"Tell me about a time when you had to solve a problem with incomplete information.",
        ],
        "communication": [
            f"Describe a time you had to explain a technical concept to a non-technical stakeholder.",
            f"How do you handle disagreements in a team setting?",
            f"Tell me about a complex technical document or presentation you created.",
        ],
        "collaboration": [
            f"Tell me about a cross-functional project you worked on as a {job_role}.",
            f"How do you handle conflicting priorities across teams?",
            f"Describe a time you mentored a junior team member.",
        ],
        "leadership": [
            f"Describe your leadership style as a {job_role}. Provide a specific example.",
            f"Tell me about a time you had to influence without authority.",
            f"How do you handle underperformance on your team?",
        ],
        "project_management": [
            f"How do you estimate effort and manage timelines in your {job_role} work?",
            f"Describe a project that went off track and how you handled it.",
            f"How do you balance feature development with technical debt?",
        ],
        "adaptability": [
            f"Tell me about a time you had to quickly learn a new technology or domain.",
            f"Describe a situation where your initial approach failed and you had to pivot.",
        ],
        "innovation": [
            f"Describe an innovative solution you proposed in your {job_role} capacity.",
            f"Tell me about a time you improved an existing process or system significantly.",
        ],
    }
    base_templates = templates.get(competency)
    if base_templates:
        if difficulty >= 5:
            return [
                f"{q} In your answer, include senior-level trade-offs, risks, and how you would scale this approach." 
                for q in base_templates
            ]
        return base_templates
    comp_name = competency.replace("_", " ").title()
    if difficulty >= 5:
        return [
            f"Tell me about your strongest {comp_name} skills in your {job_role} role. Provide a specific example and describe senior-level trade-offs.",
            f"Describe a time when {comp_name} was critical to achieving a goal. What did you do, and how did you balance risk versus reward?",
            f"How do you keep improving your {comp_name} abilities? Share a concrete example that highlights complexity and ownership.",
        ]
    return [
        f"Tell me about your strongest {comp_name} skills in your {job_role} role. Provide a specific example.",
        f"Describe a time when {comp_name} was critical to achieving a goal. What did you do?",
        f"How do you keep improving your {comp_name} abilities? Share a concrete example.",
    ]


def _fallback_question(competency: str, job_role: str, difficulty: int) -> str:
    if difficulty >= 5:
        return (
            f"Tell me about your experience with senior-level {competency.replace('_', ' ')} in your {job_role} role. "
            f"What complex challenges have you faced, what were the trade-offs, and how did you scale your solution?"
        )
    return (
        f"Tell me about your experience with {competency.replace('_', ' ')} in your {job_role} role. "
        f"What specific challenges have you faced and how did you overcome them?"
    )


def _count_competency_questions(questions: list, competency: str) -> int:
    if not questions:
        return 0
    return sum(1 for q in questions if q.get("competency") == competency)
