import logging
from app.rag.retriever import retrieve_company_context

logger = logging.getLogger(__name__)


def retrieval_agent(state):
    try:
        if not state.get("job_role"):
            logger.warning("Missing job_role in retrieval state")
            state["company_context"] = ""
            return state

        context = retrieve_company_context(state["job_role"])
        state["company_context"] = context
        logger.info("Company context retrieved")
        return state

    except Exception as e:
        logger.error(f"Error in retrieval_agent: {str(e)}")
        state["company_context"] = f"Error retrieving context: {str(e)}"
        return state