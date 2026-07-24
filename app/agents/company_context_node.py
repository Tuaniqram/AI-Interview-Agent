import logging
import time
from typing import TypedDict
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)

_session_context_cache: dict[str, tuple[float, list[dict]]] = {}
_MAX_CACHE_SIZE = 100
_CACHE_TTL = 600


async def department_context_node(state: InterviewState) -> InterviewState:
    session_id = state.get('session_id')
    department_id = state.get('department_id')
    job_role = state.get('job_role')

    if not department_id:
        logger.warning("No department_id provided, RAG context will be empty")
        return {
            **state,
            'department_context': [],
            'department_requirements': '',
            'rag_metadata': {'success': False, 'reason': 'no_department_id'}
        }

    cache_key = f"{session_id}:{department_id}"
    if cache_key in _session_context_cache:
        cache_time, cached = _session_context_cache[cache_key]
        if time.time() - cache_time < _CACHE_TTL:
            logger.info(f"Using cached RAG context for session {session_id}")
            return {
                **state,
                'department_context': cached['department_context'],
                'department_requirements': cached['department_requirements'],
                'rag_metadata': {**cached['rag_metadata'], 'cached': True}
            }
        else:
            del _session_context_cache[cache_key]

    try:
        from app.rag.pinecone_store import get_department_retriever
        import asyncio

        query = f"""
        Department interview requirements
        Role: {job_role}
        Generate suitable interview questions
        Focus on: job responsibilities, technical requirements, department challenges
        """

        t0 = time.time()

        def _retrieve(department_id, query):
            r = get_department_retriever(department_id)
            return r.invoke(query)

        docs = await asyncio.wait_for(
            asyncio.to_thread(_retrieve, department_id, query),
            timeout=15.0
        )
        elapsed = time.time() - t0
        logger.info(f"Retrieved {len(docs)} documents from Pinecone for department {department_id} in {elapsed:.2f}s")

        context_docs = []
        department_requirements = ""

        for doc in docs:
            context_docs.append({
                'page_content': doc.page_content,
                'metadata': doc.metadata if hasattr(doc, 'metadata') else {}
            })
            department_requirements += doc.page_content + "\n"

        result = {
            'department_context': context_docs,
            'department_requirements': department_requirements.strip(),
            'rag_metadata': {
                'success': True,
                'department_id': department_id,
                'documents_retrieved': len(context_docs),
            }
        }

        if len(_session_context_cache) < _MAX_CACHE_SIZE:
            _session_context_cache[cache_key] = (time.time(), result)

        return {**state, **result}

    except Exception as e:
        logger.error(f"RAG retrieval failed for department {department_id}: {e}")
        return {
            **state,
            'department_context': [],
            'department_requirements': '',
            'rag_metadata': {
                'success': False,
                'department_id': department_id,
                'error': str(e)
            }
        }
