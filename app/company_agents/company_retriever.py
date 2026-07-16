import logging

from app.rag.pinecone_store import get_company_retriever

logger = logging.getLogger(__name__)


def company_retriever(state):

    company_id = state["company_id"]
    job_role = state["job_role"]

    retriever = get_company_retriever(company_id)

    docs = retriever.invoke(
        f"""
        Company interview requirements

        Role:
        {job_role}

        Generate suitable interview questions
        """
    )

    context = "\n".join(
        doc.page_content
        for doc in docs
    )

    state["company_context"] = context

    return state