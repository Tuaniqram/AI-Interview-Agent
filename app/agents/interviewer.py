import logging
from app.models.llm import llm

logger = logging.getLogger(__name__)


def interview_agent(state):
    try:
        if not state.get('job_role') or not state.get('company_context'):
            logger.warning("Missing job_role or company_context in interview state")
            state["question"] = "Unable to generate question: missing context"
            return state

        prompt = f"""
You are a professional technical interviewer.

Company requirements:

{state["company_context"]}

Candidate role:

{state["job_role"]}

Generate one interview question based on company requirements.
"""

        response = llm.invoke(prompt)
        state["question"] = response.content
        logger.info("Interview question generated")
        return state

    except Exception as e:
        logger.error(f"Error in interview_agent: {str(e)}")
        state["question"] = f"Error generating question: {str(e)}"
        return state