"""
Pinecone vector store operations with singleton client/embedding reuse.
"""
import os
import logging

from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()
logger = logging.getLogger(__name__)

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# Module-level singletons — created once, reused across all calls
_pinecone_client: Pinecone | None = None
_embedding_model: HuggingFaceEmbeddings | None = None


def get_pinecone_client() -> Pinecone:
    global _pinecone_client
    if _pinecone_client is None:
        _pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        logger.info("Pinecone client initialized")
    return _pinecone_client


def get_embedding() -> HuggingFaceEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        logger.info("Embedding model initialized")
    return _embedding_model


def get_index():
    return get_pinecone_client().Index(INDEX_NAME)


def store_company_knowledge(chunks, company_id, doc_id=None):
    namespace = f"company_{company_id}"
    if doc_id:
        for chunk in chunks:
            chunk.metadata["doc_id"] = str(doc_id)
    vector_store = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=get_embedding(),
        index_name=INDEX_NAME,
        namespace=namespace
    )
    return vector_store


def delete_company_knowledge(company_id, doc_id):
    """Delete all vectors for a specific document from Pinecone."""
    try:
        index = get_index()
        namespace = f"company_{company_id}"
        index.delete(
            filter={"doc_id": str(doc_id)},
            namespace=namespace
        )
        logger.info(f"Deleted vectors for doc_id={doc_id} in namespace={namespace}")
    except Exception as e:
        logger.warning(f"Failed to delete vectors from Pinecone: {e}")


def get_company_retriever(company_id):
    namespace = f"company_{company_id}"
    vector_store = PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=get_embedding(),
        namespace=namespace
    )
    return vector_store.as_retriever(
        search_kwargs={"k": 5}
    )   
