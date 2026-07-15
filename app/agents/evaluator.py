import logging
from app.models.llm import llm

logger = logging.getLogger(__name__)


def evaluator_agent(state):
    try:
        if not state.get('question') or not state.get('candidate_answer'):
            logger.warning("Missing question or candidate answer in evaluator state")
            state["feedback"] = "Error: Missing question or answer"
            return state

        prompt = f"""
You are an interview evaluator.

Question:

{state['question']}

Candidate Answer:

{state['candidate_answer']}

Evaluate the answer.

Return:

Score: (0-10)
Strength:
Weakness:
Improvement:
"""

        response = llm.invoke(prompt)
        state["feedback"] = response.content
        logger.info("Evaluation completed")
        return state

    except Exception as e:
        logger.error(f"Error in evaluator_agent: {str(e)}")
        state["feedback"] = f"Error: {str(e)}"
        return state