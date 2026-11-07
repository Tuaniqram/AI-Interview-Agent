"""Company intelligence builder — assembles the V5 ``company_brain`` for a
session. Fully best-effort: RAG retrieval and LLM enrichment degrade to
deterministic keyword analysis so a session can always start.
"""
import logging

from app.intelligence._helpers import parse_llm_json_with_retry
from app.intelligence.document_analyzer import analyze_documents

logger = logging.getLogger(__name__)


async def build_company_brain(
    *,
    org_id: str | None = None,
    department_id: int | str | None = None,
    job_role: str = "",
    documents: list[dict] | None = None,
    use_rag: bool = True,
    use_llm: bool = True,
) -> dict:
    """Build a ``company_brain`` dict.

    Retrieves the organization's documents from Pinecone when ``org_id`` is set
    and ``use_rag`` is enabled, falls back to ``documents`` when provided, and
    finally to an empty analysis. ``department_id`` is a deprecated alias for
    ``org_id`` (the IT-only schema has no departments). The LLM enrichment pass
    runs only when there is actual document content to reason about.
    """
    scope_id = org_id if org_id is not None else department_id
    rag_metadata = {
        "success": False,
        "org_id": scope_id,
        "department_id": department_id,
        "documents_retrieved": 0,
        "reason": "no_org_id",
    }

    if documents is None and scope_id is not None and use_rag:
        documents, rag_metadata = await _retrieve_org_docs(scope_id, job_role)

    documents = documents or []
    analysis = analyze_documents(documents, job_role)
    rag_metadata = dict(rag_metadata)
    rag_metadata["documents_retrieved"] = len(documents)

    brain = {
        "version": "v1",
        "org_id": scope_id,
        "department_id": department_id,
        "job_role": job_role,
        **analysis,
        "documents_analyzed": len(documents),
        "rag_metadata": rag_metadata,
        "source": "fallback",
    }

    if use_llm and documents:
        try:
            enriched = await _enrich_with_llm(brain, documents)
            brain = {**brain, **enriched, "source": "llm"}
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Company brain LLM enrichment failed ({exc}); keeping fallback")

    return brain


async def _retrieve_org_docs(org_id, job_role: str) -> tuple[list[dict], dict]:
    """Pull the top organization documents from Pinecone (best-effort)."""
    metadata = {
        "success": True,
        "org_id": org_id,
        "documents_retrieved": 0,
    }
    try:
        import asyncio

        from app.rag.pinecone_store import get_org_retriever

        def _retrieve():
            retriever = get_org_retriever(org_id)
            return retriever.invoke(
                f"{job_role or ''} company overview, role context, technical stack, "
                f"team culture, processes, challenges"
            )

        docs = await asyncio.wait_for(asyncio.to_thread(_retrieve), timeout=60.0)
        chunks = [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata if hasattr(doc, "metadata") else {},
            }
            for doc in docs
        ]
        metadata["documents_retrieved"] = len(chunks)
        return chunks, metadata
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"RAG retrieval failed for org {org_id}: {exc}")
        metadata.update({"success": False, "reason": "retrieval_failed", "error": str(exc)})
        return [], metadata


async def _enrich_with_llm(brain: dict, documents: list[dict]) -> dict:
    """Summarize the retrieved documents via LLM into a company brain."""
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    doc_text = "\n\n".join(
        f"[{i + 1}] {doc.get('page_content', '')[:1200]}"
        for i, doc in enumerate(documents)
    )

    prompt = load_prompt(
        "intelligence",
        "company_brain.md",
        job_role=brain.get("job_role", "Unknown"),
        organization_id=str(brain.get("org_id") or brain.get("department_id") or ""),
        documents=doc_text,
    )

    data = await parse_llm_json_with_retry(
        get_llm_service(), prompt, temperature=0.3, max_tokens=900, tier="cheap"
    )

    allowed = {"summary", "mission", "tech_stack", "process", "culture", "challenges", "role_context"}
    cleaned = {k: v for k, v in data.items() if k in allowed}
    if not cleaned.get("summary"):
        raise ValueError("LLM company brain missing summary")
    return cleaned
