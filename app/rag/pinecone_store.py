"""
Pinecone vector store operations with singleton client/embedding reuse.
"""
import os
import logging
import threading

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore

from app.services import content_cache

load_dotenv()
logger = logging.getLogger(__name__)

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# Module-level singletons — created once, reused across all calls
_pinecone_client: Pinecone | None = None
_embedding_model: Embeddings | None = None
_embedding_lock = threading.Lock()  # the startup warm-up and a first request can race to create the backend


def get_pinecone_client() -> Pinecone:
    global _pinecone_client
    if _pinecone_client is None:
        _pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        logger.info("Pinecone client initialized")
    return _pinecone_client


def get_embedding() -> Embeddings:
    """The configured embedding backend (hosted API or local model; see app/rag/embeddings.py)."""
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                from app.rag.embeddings import build_embeddings

                _embedding_model = build_embeddings()
                logger.info("Embedding backend initialized")
    return _embedding_model


def get_index():
    return get_pinecone_client().Index(INDEX_NAME)


def org_namespace(org_id) -> str:
    """Physical Pinecone namespace of an organization's documents.

    Organization documents are ingested under ``department_{org_id}`` (the IT-only
    schema has no departments, so the id is the organization id). The prefix is
    kept so already-indexed documents stay readable without re-ingestion.
    """
    return f"department_{org_id}"


def physical_namespace(org_id) -> str:
    """The namespace actually used in Pinecone: the logical one plus the active embedding model's suffix.

    ``org_namespace`` is the name recorded in the database and stays the same whatever model is in use. Vectors
    from different embedding models must not share a namespace, so a non-MiniLM backend gets a suffix; until its
    documents are re-indexed, searching finds nothing (safe) instead of comparing across models (garbage).
    """
    from app.rag.embeddings import embedding_namespace_suffix

    return org_namespace(org_id) + embedding_namespace_suffix()


class CachedEmbeddings(Embeddings):
    """Document vectors kept by content hash, so re-indexing unchanged text is not paid for again."""

    def __init__(self, inner: Embeddings):
        self.inner = inner

    def _key(self, text: str) -> str:
        from app.rag.embeddings import embedding_namespace_suffix

        return content_cache.key("embedding", type(self.inner).__name__, embedding_namespace_suffix(), text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        keys = [self._key(t) for t in texts]
        vectors = content_cache.get_many_sync(keys)
        missing = [i for i, v in enumerate(vectors) if v is None]
        if missing:
            fresh = self.inner.embed_documents([texts[i] for i in missing])
            for i, vector in zip(missing, fresh):
                vectors[i] = [float(x) for x in vector]
            content_cache.put_many_sync({keys[i]: vectors[i] for i in missing}, content_cache.ORG_TTL_S)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.inner.embed_query(text)


def store_org_knowledge(chunks, org_id, doc_id=None):
    namespace = physical_namespace(org_id)
    if doc_id:
        for chunk in chunks:
            chunk.metadata["doc_id"] = str(doc_id)
    vector_store = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=CachedEmbeddings(get_embedding()),
        index_name=INDEX_NAME,
        namespace=namespace
    )
    return vector_store


def delete_org_knowledge(org_id, doc_id):
    try:
        index = get_index()
        # Delete from the plain namespace AND the active model's one: the document may have been indexed under either.
        from app.rag.embeddings import PineconeEmbeddings

        base = org_namespace(org_id)
        for namespace in dict.fromkeys([base, base + PineconeEmbeddings.namespace_suffix, physical_namespace(org_id)]):
            index.delete(
                filter={"doc_id": str(doc_id)},
                namespace=namespace
            )
            logger.info(f"Deleted vectors for doc_id={doc_id} in namespace={namespace}")
    except Exception as e:
        logger.warning(f"Failed to delete vectors from Pinecone: {e}")


def get_org_retriever(org_id, k: int = 5):
    """Retriever over an organization's uploaded documents (org-scoped RAG)."""
    vector_store = PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=get_embedding(),
        namespace=physical_namespace(org_id)
    )
    return vector_store.as_retriever(
        search_kwargs={"k": k}
    )
