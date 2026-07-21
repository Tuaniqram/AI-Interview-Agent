"""
Company Context Retrieval Node - LangGraph Node Agent
Retrieves company-specific context from Pinecone RAG.
Results cached per session — only queries Pinecone once.
"""
import logging
import time
from typing import TypedDict
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)

_session_context_cache: dict[str, tuple[float, list[dict]]] = {}
_MAX_CACHE_SIZE = 100
_CACHE_TTL = 600  # 10 minutes


async def company_context_node(state: InterviewState) -> InterviewState:
    session_id = state.get('session_id')
    company_id = state.get('company_id')
    job_role = state.get('job_role')

    if not company_id:
        logger.warning("No company_id provided, RAG context will be empty")
        return {
            **state,
            'company_context': [],
            'company_requirements': '',
            'rag_metadata': {'success': False, 'reason': 'no_company_id'}
        }

    cache_key = f"{session_id}:{company_id}"
    if cache_key in _session_context_cache:
        cache_time, cached = _session_context_cache[cache_key]
        if time.time() - cache_time < _CACHE_TTL:
            logger.info(f"Using cached RAG context for session {session_id}")
            return {
                **state,
                'company_context': cached['company_context'],
                'company_requirements': cached['company_requirements'],
                'rag_metadata': {**cached['rag_metadata'], 'cached': True}
            }
        else:
            del _session_context_cache[cache_key]

    try:
        from app.rag.pinecone_store import get_company_retriever
        import asyncio

        query = f"""
        Company interview requirements
        Role: {job_role}
        Generate suitable interview questions
        Focus on: job responsibilities, technical requirements, company challenges
        """

        t0 = time.time()

        def _retrieve(company_id, query):
            r = get_company_retriever(company_id)
            return r.invoke(query)

        docs = await asyncio.wait_for(
            asyncio.to_thread(_retrieve, company_id, query),
            timeout=15.0
        )
        elapsed = time.time() - t0
        logger.info(f"Retrieved {len(docs)} documents from Pinecone for company {company_id} in {elapsed:.2f}s")

        context_docs = []
        company_requirements = ""

        for doc in docs:
            context_docs.append({
                'page_content': doc.page_content,
                'metadata': doc.metadata if hasattr(doc, 'metadata') else {}
            })
            company_requirements += doc.page_content + "\n"

        result = {
            'company_context': context_docs,
            'company_requirements': company_requirements.strip(),
            'rag_metadata': {
                'success': True,
                'company_id': company_id,
                'documents_retrieved': len(context_docs),
            }
        }

        if len(_session_context_cache) < _MAX_CACHE_SIZE:
            _session_context_cache[cache_key] = (time.time(), result)

        return {**state, **result}

    except Exception as e:
        logger.error(f"RAG retrieval failed for company {company_id}: {e}")
        return {
            **state,
            'company_context': [],
            'company_requirements': '',
            'rag_metadata': {
                'success': False,
                'company_id': company_id,
                'error': str(e)
            }
        }