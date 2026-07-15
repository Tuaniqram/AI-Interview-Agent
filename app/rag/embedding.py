import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def split_documents(documents):
    try:
        if not documents:
            logger.warning("No documents provided to split_documents")
            return []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )

        chunks = splitter.split_documents(documents)
        logger.info(f"Split {len(documents)} documents into {len(chunks)} chunks")
        return chunks

    except Exception as e:
        logger.error(f"Error splitting documents: {str(e)}")
        raise