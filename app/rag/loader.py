import logging
import os
from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger(__name__)


def load_pdf(path):
    try:
        if not os.path.exists(path):
            logger.error(f"PDF file not found: {path}")
            raise FileNotFoundError(f"PDF file not found: {path}")

        loader = PyPDFLoader(path)
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} pages from {path}")
        return documents

    except Exception as e:
        logger.error(f"Error loading PDF: {str(e)}")
        raise