"""
Company Context Retrieval Node - LangGraph Node Agent
Retrieves company-specific context from Pinecone RAG.
"""
import logging
from typing import TypedDict
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


async def company_context_node(state: InterviewState) -> InterviewState:
    """
    Retrieve company context from Pinecone RAG.
    
    Args:
        state: Current interview state
        
    Returns:
        Updated state with company context
    """
    company_id = state.get('company_id')
    job_role = state.get('job_role')
    
    if not company_id:
        # RAG not available, continue without company context
        logger.warning("No company_id provided, RAG context will be empty")
        return {
            **state,
            'company_context': [],
            'company_requirements': '',
            'rag_metadata': {'success': False, 'reason': 'no_company_id'}
        }
    
    try:
        # Import RAG service (lazy import to avoid circular dependencies)
        from app.rag.pinecone_store import get_company_retriever
        
        # Get retriever for this company
        retriever = get_company_retriever(company_id)
        
        # Build query for RAG
        query = f"""
        Company interview requirements
        Role: {job_role}
        Generate suitable interview questions
        Focus on: job responsibilities, technical requirements, company challenges
        """
        
        # Retrieve documents (retriever is synchronous)
        docs = retriever.invoke(query)
        logger.info(f"Retrieved documents using synchronous retriever")
        
        # Extract and summarize context
        context_docs = []
        company_requirements = ""
        
        for doc in docs:
            context_docs.append({
                'page_content': doc.page_content,
                'metadata': doc.metadata if hasattr(doc, 'metadata') else {}
            })
            company_requirements += doc.page_content + "\n"
        
        logger.info(f"Retrieved {len(context_docs)} documents from Pinecone for company {company_id}")
        
        return {
            **state,
            'company_context': context_docs,
            'company_requirements': company_requirements.strip(),
            'rag_metadata': {
                'success': True,
                'company_id': company_id,
                'documents_retrieved': len(context_docs),
                'query_length': len(query)
            }
        }
        
    except Exception as e:
        logger.error(f"RAG retrieval failed for company {company_id}: {e}")
        # Fall back to empty context
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