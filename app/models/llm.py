import os
import logging
from typing import Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

load_dotenv()

class FallbackLLM:
    """Tries multiple LLMs in sequence on failure."""

    def __init__(self, models: list[ChatOpenAI]):
        self._models = models

    async def ainvoke(self, messages: list, config: dict | None = None, **kwargs: Any) -> Any:
        last_error = None
        for model in self._models:
            try:
                return await model.ainvoke(messages, config, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning("Model %s failed, trying next: %s", model.model_name, e)
        raise RuntimeError("All models failed") from last_error

    @property
    def model_name(self) -> str:
        return "+".join(m.model_name for m in self._models)


_LLM_CONFIGS: list[dict[str, str | None]] = [
    {"model": "one", "base_url": "http://localhost:20128/v1", "api_key": None},
    {"model": "openrouter/auto-beta", "base_url": "https://openrouter.ai/api/v1", "api_key": os.getenv("OPENROUTER_API_KEY")},
]


def _build_llm_instance(config: dict[str, str | None]) -> ChatOpenAI:
    api_key = config["api_key"] or "sk-no-key"
    return ChatOpenAI(
        model=str(config["model"]),
        temperature=0.7,
        max_tokens=2048,
        openai_api_key=api_key,
        openai_api_base=str(config["base_url"]),
    )


llm: FallbackLLM = FallbackLLM([_build_llm_instance(c) for c in _LLM_CONFIGS])

logger.info("LLM initialized with fallback chain: %s", llm.model_name)


_llm_registry: dict[str, FallbackLLM] = {"openrouter": llm}


def get_llm(name: str | None = None) -> FallbackLLM:
    if name is None:
        name = os.getenv("LLM_PROVIDER", "openrouter")
    if name not in _llm_registry:
        raise ValueError(f"Unknown LLM provider: {name}")
    return _llm_registry[name]