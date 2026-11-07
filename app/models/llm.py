import os
import re
import time
import logging
from typing import Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

load_dotenv()

class EmptyModelResponse(RuntimeError):
    """A model answered successfully at the HTTP level but with no text."""


class FallbackLLM:
    """Tries multiple LLMs in sequence on failure, with a per-model circuit breaker.

    A provider that fails is remembered and skipped for a cool-down, so a dead model (a retired
    model id returning 404, a local gateway returning 410, a revoked key) no longer costs a
    network round trip on *every* call before the chain reaches one that works.

    * permanent errors (401/403/404/410): skipped for ``PERMANENT_COOLDOWN_S``
    * transient errors (429, 5xx, timeouts, connection): skipped for ``TRANSIENT_COOLDOWN_S``
    * when every model is cooling down they are all still tried (healthy ones first), so the
      chain degrades to the old behaviour instead of refusing to answer.
    """

    PERMANENT_STATUS = frozenset({401, 403, 404, 410})
    PERMANENT_COOLDOWN_S = 15 * 60
    TRANSIENT_COOLDOWN_S = 30

    def __init__(self, models: list[ChatOpenAI], clock=time.monotonic):
        self._models = models
        self._clock = clock
        self._skip_until: dict[int, float] = {}

    def _sanitize_error(self, error: Exception) -> str:
        msg = str(error)
        for key in ("api_key", "apikey", "authorization", "x-api-key"):
            if key.lower() in msg.lower():
                msg = re.sub(r'(api_key["\']?\s*[:=]\s*["\']?)[^"\'}\s,]+', r'\1***', msg, flags=re.IGNORECASE)
        return msg[:500]

    @staticmethod
    def _status_of(error: Exception) -> int | None:
        status = getattr(error, "status_code", None)
        if status is None:
            status = getattr(getattr(error, "response", None), "status_code", None)
        return status if isinstance(status, int) else None

    def _candidates(self) -> list:
        now = self._clock()
        healthy = [m for m in self._models if self._skip_until.get(id(m), 0.0) <= now]
        # Last resort: models still cooling down, soonest-to-recover first (a 30s transient cool-down
        # before a 15 min "this model id is retired" one).
        cooling = sorted(
            (m for m in self._models if self._skip_until.get(id(m), 0.0) > now),
            key=lambda m: self._skip_until[id(m)],
        )
        return healthy + cooling  # never empty while there is at least one model

    def _record_failure(self, model, error: Exception) -> None:
        permanent = self._status_of(error) in self.PERMANENT_STATUS
        cooldown = self.PERMANENT_COOLDOWN_S if permanent else self.TRANSIENT_COOLDOWN_S
        self._skip_until[id(model)] = self._clock() + cooldown

    def _record_success(self, model) -> None:
        self._skip_until.pop(id(model), None)

    async def ainvoke(self, messages: list, config: dict | None = None, **kwargs: Any) -> Any:
        last_error = None
        for model in self._candidates():
            try:
                result = await model.ainvoke(messages, config, **kwargs)
                content = getattr(result, "content", None)
                if isinstance(content, str) and not content.strip():
                    # Free/overloaded models often answer 200 with an empty body. Treat it as a failed
                    # attempt so the next provider is tried, instead of handing every caller "".
                    raise EmptyModelResponse(f"{model.model_name} returned an empty response")
                self._record_success(model)
                return result
            except Exception as e:
                last_error = e
                self._record_failure(model, e)
                logger.warning("Model %s failed, trying next: %s", model.model_name, self._sanitize_error(e))
        raise RuntimeError("All models failed") from last_error

    async def astream(self, messages, config=None, **kwargs):
        """Stream tokens from the first available model."""
        last_error = None
        for model in self._candidates():
            try:
                async for chunk in model.astream(messages, config, **kwargs):
                    if hasattr(chunk, 'content') and chunk.content:
                        yield chunk.content
                self._record_success(model)
                return
            except Exception as e:
                last_error = e
                self._record_failure(model, e)
        raise RuntimeError("All models failed") from last_error

    @property
    def model_name(self) -> str:
        return "+".join(m.model_name for m in self._models)


_LLM_CONFIGS: list[dict[str, str | None]] = [
    {"model": "llama-3.3-70b-versatile", "base_url": "https://api.groq.com/openai/v1", "api_key": os.getenv("GROQ_API_KEY")},
    {"model": "one", "base_url": "http://localhost:20128/v1", "api_key": None},
    {"model": "openrouter/free", "base_url": "https://openrouter.ai/api/v1", "api_key": os.getenv("OPENROUTER_API_KEY")},
]

# Cheap tier — small/fast models for extraction, formatting and classification.
# Falls back to the local model and finally the strong chain so it never
# fails outright when no cheap provider is configured.
_CHEAP_LLM_CONFIGS: list[dict[str, str | None]] = [
    {"model": "llama-3.1-8b-instant", "base_url": "https://api.groq.com/openai/v1", "api_key": os.getenv("GROQ_API_KEY")},
    {"model": "one", "base_url": "http://localhost:20128/v1", "api_key": None},
    *_LLM_CONFIGS,
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
cheap_llm: FallbackLLM = FallbackLLM([_build_llm_instance(c) for c in _CHEAP_LLM_CONFIGS])

logger.info("LLM initialized with fallback chain: %s", llm.model_name)
logger.info("LLM cheap tier initialized with fallback chain: %s", cheap_llm.model_name)


_llm_registry: dict[str, FallbackLLM] = {
    "strong": llm,
    "cheap": cheap_llm,
    "openrouter": llm,
}


def get_llm(name: str | None = None) -> FallbackLLM:
    if name is None:
        name = os.getenv("LLM_PROVIDER", "openrouter")
    if name not in _llm_registry:
        raise ValueError(f"Unknown LLM provider: {name}")
    return _llm_registry[name]