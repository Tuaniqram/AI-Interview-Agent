import logging
from app.models.llm import llm

logger = logging.getLogger(__name__)


def evaluator_agent(state):
    try:
        if not state.get('question') or not state.get('candidate_answer'):
            logger.warning("Missing question or candidate answer in evaluator state")
            state["feedback"] = "Error: Missing question or answer"
            return state

        company_context = state.get('company_context', 'General technical role')
        job_role = state.get('job_role', 'Software Engineer')

        prompt = f"""
You are an experienced technical interviewer evaluating a candidate's response.
Your feedback style is constructive, honest, and helpful - like a real interviewer would give.

Job Role: {job_role}

Company Requirements:
{company_context}

Question Asked:
{state['question']}

Candidate's Answer:
{state['candidate_answer']}

---

Provide feedback as if you're giving real interview feedback to the candidate. Include:

1. **Score**: Rate from 1-10 (be realistic)

2. **What they did well**: Be specific about strengths you noticed

3. **Areas for growth**: What could they have done better?

4. **Next step question**: If you were continuing the interview, what would be a natural follow-up question to dig deeper?

5. **Overall impression**: One sentence summary of how you'd rate them for this role

Write this like you're actually giving feedback to the candidate - conversational, direct, and honest.
Don't be harsh, but be truthful. Help them understand how they came across.
"""

        response = llm.invoke(prompt)
        feedback_text = response.content.strip()
        
        state["feedback"] = feedback_text
        state["interview_complete"] = True
        
        logger.info("Evaluation completed")
        return state

    except Exception as e:
        logger.error(f"Error in evaluator_agent: {str(e)}")
        state["feedback"] = f"Error: {str(e)}"
        return state