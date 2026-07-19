"""
Question Generation Node - LangGraph Node Agent
Generates adaptive interview questions using LLM and company context.
CRITICAL: NO HARDCODED TEMPLATES - Always generates via AI.
"""
import logging
from typing import TypedDict
from app.graph.interview_state import InterviewState
from app.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


async def question_generation_node(state: InterviewState) -> InterviewState:
    """
    Generate the next interview question using AI.
    IMPORTANT: Uses company context from RAG and AI generation.
    NEVER returns hardcoded templates.
    
    Args:
        state: Current interview state
        
    Returns:
        Updated state with generated question
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt
    
    # Extract required fields
    job_role = state.get('job_role')
    phase = state.get('current_phase')
    difficulty = state.get('difficulty_level', 1)
    conversation_history = state.get('conversation_history', [])
    company_requirements = state.get('company_requirements', '')
    candidate_profile = state.get('candidate_profile', '{}')
    question_number = state.get('question_number', 0)
    
    logger.info(f"Generating adaptive question: Phase={phase}, Difficulty={difficulty}, Q#{question_number}")
    
    # Increment question number for next question
    new_question_number = question_number + 1
    logger.info(f"Incrementing question_number from {question_number} to {new_question_number}")
    
    # Build conversation history summary
    history_summary = ""
    for h in conversation_history[-5:]:  # Last 5 exchanges
        role = h.get('role', '')
        content = h.get('content', '')
        history_summary += f"\n{role}: {content}\n"
    
    # Construct prompt with ALL context
    prompt = f"""
You are an expert technical interviewer conducting a technical interview for the role of "{job_role}".

COMPANY CONTEXT (from company documents):
---
{company_requirements}
---

CANDIDATE PROFILE:
---
{candidate_profile}
---

INTERVIEW PHASE: {phase}
DIFFICULTY LEVEL: {difficulty} (1=Easy, 2=Medium, 3=Hard)
QUESTION NUMBER: {question_number}

CONVERSATION HISTORY (recent exchanges):
{history_summary}

INSTRUCTIONS:
1. Generate ONE adaptive interview question that tests the candidate's competence in this role.
2. ALWAYS include references to company context when relevant.
3. Adjust difficulty based on phase:
   - INTRO: Simple icebreaker, 1-2 sentences
   - EXPERIENCE: Behavioral question about past projects, 1-2 sentences
   - TECHNICAL: Deep technical question, 1-2 sentences
   - BEHAVIORAL: Situational question about soft skills, 1-2 sentences
   - CONCLUSION: Wrap-up question, 1-2 sentences
4. Focus on real job responsibilities mentioned in company context.
5. Question must be specific, measurable, and test actual knowledge.
6. Output ONLY the question text. Do NOT include:
   - Introductory text
   - Context leeway
   - Code examples (unless asked)
   
Output format:
Question: <your adaptive question here>
"""
    
    try:
        # Use LLM service
        llm_service = get_llm_service()
        
        logger.debug(f"Sending prompt to LLM (len={len(prompt)})")
        
        # Generate question
        question = await llm_service.invoke(
            prompt=prompt,
            temperature=0.8,  # Higher temperature for more adaptive variety
            max_tokens=200  # Short, concise question
        )
        
        # Clean up response (remove any extra text)
        question = question.strip()
        if question.startswith("Question:"):
            question = question[9:].strip()
        
        if not question or question == "":
            # NO HARDCODED FALLBACK - Retry LLM with simplified prompt
            logger.warning("LLM returned empty question, retrying with simplified prompt")
            simplified_prompt = f"""
You are an interviewer for the role: {job_role}.
Phase: {phase}. Difficulty: {difficulty}.
Company context: {company_requirements[:500] if company_requirements else 'N/A'}
Candidate profile: {candidate_profile[:300] if candidate_profile else 'N/A'}

Generate ONE adaptive interview question. Output ONLY the question text (no prefix).
"""
            question = await llm_service.invoke(
                prompt=simplified_prompt,
                temperature=0.9,
                max_tokens=200
            )
            question = question.strip()
            if question.startswith("Question:"):
                question = question[9:].strip()

            if not question or question == "":
                # Final failure - raise instead of hardcoding
                logger.error("LLM returned empty question after retry")
                raise LLMServiceError("LLM failed to generate a valid question after retry")

        logger.info(f"Generated adaptive question: {question[:100]}...")
        
        # Update state with new question and incremented question_number
        new_state: InterviewState = {
            **state,
            'current_question': question,
            'question_number': new_question_number,
            'rag_metadata': {
                **state.get('rag_metadata', {}),
                'question_generated_by_ai': True,
                'question_number': new_question_number,
                'ai_generation_params': {
                    'temperature': 0.8,
                    'max_tokens': 200
                }
            }
        }
        
        return new_state
        
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        # NO HARDCODED FALLBACK - propagate error so workflow can handle it
        new_state: InterviewState = {
            **state,
            'current_question': None,
            'question_number': question_number + 1,
            'rag_metadata': {
                **state.get('rag_metadata', {}),
                'question_generated_by_ai': False,
                'question_generation_failed': True,
                'error': str(e)
            }
        }
        # Re-raise so the LangGraph workflow / orchestrator can surface the error
        raise
