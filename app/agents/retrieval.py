from app.rag.retriever import retrieve_company_context


def retrieve_context(state):

    context = retrieve_company_context(
        state.get("question", state.get("job_role", ""))
    )

    state["context"] = context

    return state