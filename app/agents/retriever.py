import logging
from app.rag.retriever import retrieve_company_context

logger = logging.getLogger(__name__)


def retrieval_agent(state):
    try:
        if not state.get("job_role"):
            logger.warning("Missing job_role in retrieval state")
            state["company_context"] = ""
            return state

        # Retrieve company context from knowledge base
        context = retrieve_company_context(state["job_role"])
        
        # Format context in a more readable way for the interviewer
        if context:
            formatted_context = f"""
Key Requirements for {state['job_role']}:
{context}
"""
        else:
            formatted_context = f"General requirements for {state['job_role']}"
        
        state["company_context"] = formatted_context
        logger.info("Company context retrieved")
        return state

    except Exception as e:
        logger.error(f"Error in retrieval_agent: {str(e)}")
        state["company_context"] = f"Error retrieving context: {str(e)}"
        return state