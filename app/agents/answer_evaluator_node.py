"""
Answer Evaluation Node - LangGraph Node Agent
Evaluates candidate answers with detailed scoring and feedback.
"""
import logging
from typing import TypedDict
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


async def answer_evaluator_node(state: InterviewState) -> InterviewState:
    """
    Evaluate candidate answer and provide detailed feedback.
    
    Args:
        state: Current interview state
        
    Returns:
        Updated state with evaluation results
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt
    
    job_role = state.get('job_role')
    question = state.get('current_question', '')
    candidate_answer = state.get('candidate_answer', '')
    company_requirements = state.get('company_requirements', '')
    difficulty = state.get('difficulty_level', 1)
    phase = state.get('current_phase')
    
    logger.info(f"Evaluating answer: Phase={phase}, Difficulty={difficulty}")
    
    prompt = f"""
You are an expert technical interviewer evaluating a candidate's response.

COMPANY CONTEXT:
{company_requirements}

JOB ROLE:
{job_role}

QUESTION ASKED:
{question}

CANDIDATE ANSWER:
{candidate_answer}

DIFFICULTY: {difficulty}
INTERVIEW PHASE: {phase}

EVALUATION RULES:
1. Score technical competence on scale 0.0-10.0
2. Score communication on scale 0.0-10.0  
3. Identify 3 key strengths with specific examples
4. Identify 3 areas for improvement
5. Provide detailed feedback on what was good/bad
6. Suggest specific follow-up question approach

Return ONLY valid JSON.

Expected:
```json
{{
 "score":8,
 "technical_score":8,
 "communication_score":7,
 "strengths":[],
 "weaknesses":[],
 "feedback":""
}}
```

JSON Output:
"""
    
    try:
        llm_service = get_llm_service()
        
        response = await llm_service.invoke(
            prompt=prompt,
            temperature=0.3,
            max_tokens=1024
        )
        
        # Log raw response for debugging
        logger.info("Raw evaluation response: %s", response)
        
        # Clean up markdown code blocks from response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]  # Remove ```json
        if response.startswith("```"):
            response = response[3:]  # Remove ```
        if response.endswith("```"):
            response = response[:-3]  # Remove closing ```
        response = response.strip()
        
        # Parse JSON response
        import json
        score_data = None

        try:
            score_data = json.loads(response)
        except json.JSONDecodeError:
            logger.debug("Full response parse failed, attempting extraction")

        if not score_data:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    score_data = json.loads(response[start:end + 1])
                except json.JSONDecodeError as e:
                    logger.warning(f"Extracted JSON parse failed: {e}")

        if not score_data:
            logger.error(f"Failed to parse evaluation JSON. Response preview: {response[:200]}")
            raise ValueError("Failed to parse evaluation JSON")
        
        logger.info(f"Evaluation scored: Technical={score_data.get('technical_score')}, Communication={score_data.get('communication_score')}")
        
        return {
            **state,
            'evaluation_failed': False,
            'evaluation_score': float(score_data.get('score', 0.0)),
            'technical_score': float(score_data.get('technical_score', 0.0)),
            'communication_score': float(score_data.get('communication_score', 0.0)),
            'strengths': score_data.get('strengths', []),
            'weaknesses': score_data.get('weaknesses', []),
            'feedback_detail': score_data.get('feedback', ''),
            'next_action': score_data.get('next_action', 'continue'),
            'evaluation_metadata': {'raw_response': response}
        }
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        # Return error flag instead of silently defaulting to score=7
        return {
            **state,
            'evaluation_failed': True,
            'evaluation_score': None,
            'technical_score': None,
            'communication_score': None,
            'strengths': [],
            'weaknesses': [],
            'feedback_detail': f"Evaluation failed: {e}",
            'next_action': 'retry',
            'evaluation_metadata': {'error': str(e), 'failed': True}
        }