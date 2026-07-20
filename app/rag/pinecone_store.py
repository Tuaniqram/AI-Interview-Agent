import os
import logging

from dotenv import load_dotenv

from pinecone import Pinecone
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore


load_dotenv()

logger = logging.getLogger(__name__)


INDEX_NAME = os.getenv(
    "PINECONE_INDEX_NAME"
)


def get_embedding():

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


def get_index():

    pc = Pinecone(
        api_key=os.getenv("PINECONE_API_KEY")
    )

    return pc.Index(INDEX_NAME)



def store_company_knowledge(
        chunks,
        company_id,
        doc_id=None
):

    namespace = f"company_{company_id}"

    # Tag each chunk with doc_id so we can delete them later
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


def delete_company_knowledge(
        company_id,
        doc_id
):
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


def get_company_retriever(
        company_id
):

    namespace = f"company_{company_id}"


    vector_store = PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=get_embedding(),
        namespace=namespace
    )


    return vector_store.as_retriever(
        search_kwargs={
            "k":5
        }
    )   
