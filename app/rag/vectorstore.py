import logging
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

VECTOR_DB_PATH = "vector_db"


def get_embedding():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


def create_database(chunks):
    try:
        if not chunks:
            logger.warning("No chunks provided to create_database")
            return None

        db = FAISS.from_documents(
            chunks,
            get_embedding()
        )

        db.save_local(VECTOR_DB_PATH)
        logger.info(f"Vector database created and saved to {VECTOR_DB_PATH}")
        return db

    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        raise