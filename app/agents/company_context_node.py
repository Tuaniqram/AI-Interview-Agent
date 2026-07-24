import logging
import time
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)

_session_context_cache: dict[str, tuple[float, dict]] = {}
_MAX_CACHE_SIZE = 200
_CACHE_TTL = 600

_PHASE_QUERY_TEMPLATES = {
    "intro": """
Role: {job_role}
Phase: Introduction — building rapport, assessing career trajectory
Retrieve documents about: company overview, team structure, company culture, department mission
Focus areas: company values, team composition, organizational structure, role context
""",
    "experience": """
Role: {job_role}
Phase: Experience — evaluating past projects and practical experience
Retrieve documents about: technical stacks, project examples, methodologies, tools used
Focus areas: technologies used, development practices, project types, infrastructure
""",
    "technical": """
Role: {job_role}
Phase: Technical — testing core knowledge and problem-solving
Retrieve documents about: technical requirements, system architecture, technical challenges
Focus areas: technical stack details, architecture decisions, domain-specific technologies, technical debt areas
""",
    "behavioral": """
Role: {job_role}
Phase: Behavioral — assessing soft skills, teamwork, conflict resolution
Retrieve documents about: team dynamics, company values, collaboration patterns
Focus areas: team culture, communication norms, company values, cross-team collaboration
""",
    "conclusion": """
Role: {job_role}
Phase: Conclusion — final assessment and career goals
Retrieve documents about: company future, growth opportunities, company vision
Focus areas: company roadmap, career development, company mission, future initiatives
""",
}


async def department_context_node(state: InterviewState) -> InterviewState:
    session_id = state.get('session_id')
    department_id = state.get('department_id')
    job_role = state.get('job_role')
    current_phase = state.get('current_phase', 'intro')
    skills_weak = state.get('skills_weak', [])

    if not department_id:
        logger.warning("No department_id provided, RAG context will be empty")
        return {
            **state,
            'department_context': [],
            'department_requirements': '',
            'rag_metadata': {'success': False, 'reason': 'no_department_id'}
        }

    # Phase-aware cache key: different phases retrieve different documents
    cache_key = f"{session_id}:{department_id}:{current_phase}"
    if cache_key in _session_context_cache:
        cache_time, cached = _session_context_cache[cache_key]
        if time.time() - cache_time < _CACHE_TTL:
            logger.info(f"Using cached RAG context for session {session_id}, phase={current_phase}")
            return {
                **state,
                'department_context': cached['department_context'],
                'department_requirements': cached['department_requirements'],
                'rag_metadata': {**cached['rag_metadata'], 'cached': True, 'phase': current_phase}
            }

    try:
        from app.rag.pinecone_store import get_department_retriever
        import asyncio

        template = _PHASE_QUERY_TEMPLATES.get(
            current_phase,
            "Retrieve documents related to: {job_role}, department requirements"
        )
        base_query = template.format(job_role=job_role or "Unknown Role")

        # Append weak skills to focus retrieval on areas needing improvement
        skills_suffix = ""
        if skills_weak:
            skills_suffix = f"\nCandidate weak areas to address: {', '.join(skills_weak[:3])}"
        query = base_query + skills_suffix

        t0 = time.time()

        def _retrieve(department_id, query):
            r = get_department_retriever(department_id)
            return r.invoke(query)

        docs = await asyncio.wait_for(
            asyncio.to_thread(_retrieve, department_id, query),
            timeout=15.0
        )
        elapsed = time.time() - t0
        logger.info(
            f"Retrieved {len(docs)} docs for department {department_id}, "
            f"phase={current_phase} in {elapsed:.2f}s"
        )

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
                'phase': current_phase,
                'query': query,
                'documents_retrieved': len(context_docs),
            }
        }

        if len(_session_context_cache) < _MAX_CACHE_SIZE:
            _session_context_cache[cache_key] = (time.time(), result)

        return {**state, **result}

    except Exception as e:
        logger.error(f"RAG retrieval failed for department {department_id}, phase={current_phase}: {e}")
        return {
            **state,
            'department_context': [],
            'department_requirements': '',
            'rag_metadata': {
                'success': False,
                'department_id': department_id,
                'phase': current_phase,
                'error': str(e)
            }
        }
