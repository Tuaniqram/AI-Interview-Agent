import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)

VECTOR_DB_PATH = "vector_db"


def get_embedding():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


def retrieve_company_context(question):
    try:
        if not question or not isinstance(question, str):
            logger.warning("Invalid question provided to retrieve_company_context")
            return ""

        embeddings = get_embedding()

        db = FAISS.load_local(
            VECTOR_DB_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

        docs = db.similarity_search(question, k=3)

        context = "\n".join(
            doc.page_content
            for doc in docs
        )

        logger.info(f"Retrieved {len(docs)} documents for question")
        return context

    except Exception as e:
        logger.error(f"Error retrieving company context: {str(e)}")
        return f"Error: {str(e)}"