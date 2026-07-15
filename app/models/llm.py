import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    logger.error("OPENROUTER_API_KEY environment variable not set")
    raise ValueError("OPENROUTER_API_KEY environment variable is required")

llm = ChatOpenAI(
    model="openrouter/auto",
    temperature=0.7,
    openai_api_key=api_key,
    openai_api_base="https://openrouter.ai/api/v1"
)

logger.info("LLM initialized successfully")