import logging
from uuid import uuid4
from datetime import datetime, timezone

from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)

MAX_FOLLOWUPS_PER_COMPETENCY = 3


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

    difficulty = state.get("difficulty_level", 1)

    target_competency = ""
    target_hypothesis = {}

    if hypothesis_target:
        target_competency = hypothesis_target.get("competency", "")
        target_hypothesis = hypothesis_target

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

    try:
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
        )
    except Exception as e:
        logger.warning(f"Question generation error: {e}")
        question_text = _fallback_question(target_competency or "General", job_role, difficulty)

    question_id = str(uuid4())

    question_objective = {
        "question_id": question_id,
        "target_competency": target_competency,
        "target_hypothesis_id": hypothesis_target.get("id", "") if hypothesis_target else "",
        "difficulty": difficulty,
        "type": "exploratory",
    }

    questions_asked = list(previous_questions)
    questions_asked.append({
        "id": question_id,
        "text": question_text,
        "competency": target_competency,
        "difficulty": difficulty,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        **state,
        "current_question": question_text,
        "question_objective": question_objective,
        "questions_asked": questions_asked,
        "question_number": question_number + 1,
    }


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
) -> str:
    if hypothesis_text:
        direction = "positive" if "strong" in hypothesis_text.lower() else "negative"
        if direction == "positive" and followup_number > 0:
            return (
                f"You mentioned you have strength in this area. Can you walk me through a specific "
                f"challenging project where you applied advanced {target_competency.replace('_', ' ')} concepts? "
                f"What was the hardest technical problem you had to solve?"
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
        import random
        idx = min(followup_number, len(templates) - 1) if followup_number < len(templates) else 0
        return templates[idx]

    return _fallback_question(target_competency, job_role, difficulty)


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
    return templates.get(competency, [])


def _fallback_question(competency: str, job_role: str, difficulty: int) -> str:
    return (
        f"Tell me about your experience with {competency.replace('_', ' ')} in your {job_role} role. "
        f"What specific challenges have you faced and how did you overcome them?"
    )


def _count_competency_questions(questions: list, competency: str) -> int:
    if not questions:
        return 0
    return sum(1 for q in questions if q.get("competency") == competency)
