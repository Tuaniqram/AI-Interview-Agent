"""
LLM Service with retry logic, concurrency and budget limits.
Handles all LLM operations with proper error handling.
"""
import asyncio
import logging
import os
from typing import Any, AsyncGenerator, Optional

from app.models.llm import llm, get_llm
from app.exceptions import LLMBudgetExceeded, LLMServiceError, LLMTimeoutError, LLMRateLimitError
from app.services import llm_budget

logger = logging.getLogger(__name__)

# gpt-oss style models spend part of ``max_tokens`` on hidden reasoning before the first visible
# character. A caller asking for "400 tokens" means ~400 tokens of ANSWER, so the model is given that
# plus this headroom; without it a small budget returns an empty reply (finish_reason=length).
REASONING_HEADROOM_TOKENS = 1500
MAX_COMPLETION_TOKENS = 8192


# A stuck provider must cost an interview seconds, not minutes. The limit grows with the answer length the
# caller asked for: ~20 s of headroom plus the answer at a deliberately slow 40 tokens/s, between 35 s (typical
# calls take 1-5 s) and 90 s (the long final read).
MIN_REQUEST_TIMEOUT_S = 35
MAX_REQUEST_TIMEOUT_S = 90


# Plan step 10 (P10): question writing gives up on a stalled provider sooner, so the chain moves to the next
# model while the candidate is still waiting for the question.
# 15 s, not the plan's 30: in the step 10 gate a stalled question call took 34.8 s (30 s + the backup model);
# normal question calls take 1-3 s.
QUESTION_REQUEST_TIMEOUT_S = float(os.getenv("QUESTION_REQUEST_TIMEOUT_S", "15"))
# The per-answer evaluation (normally 1-7 s) may wait this long for one provider before the next is tried;
# without a cap its 2,200-token budget allowed ~85 s (a 40.5 s stall in the step 10 gate).
EVALUATOR_REQUEST_TIMEOUT_S = float(os.getenv("EVALUATOR_REQUEST_TIMEOUT_S", "25"))
# Plan step 10 (N9): calls allowed in flight at once across the whole process. 3 meant that with several live
# interviews every call queued behind the others.
LLM_MAX_CONCURRENCY = 16


def max_concurrency() -> int:
    """``LLM_MAX_CONCURRENCY`` (default 16), read when the service is created."""
    try:
        return max(1, int(os.getenv("LLM_MAX_CONCURRENCY", str(LLM_MAX_CONCURRENCY))))
    except ValueError:
        return LLM_MAX_CONCURRENCY
# Whole-chain attempts for calls made while the candidate waits (question, evaluation, clarification).
TURN_ATTEMPTS = 2


def request_timeout(requested: int, cap: float | None = None) -> float:
    """Per-request timeout in seconds for a call that asks for ``requested`` tokens of answer (``cap``: an
    upper bound for latency-sensitive calls, never below 5 s)."""
    timeout = float(min(MAX_REQUEST_TIMEOUT_S, max(MIN_REQUEST_TIMEOUT_S, 20 + (max(1, int(requested)) + 400) / 40)))
    return min(timeout, max(5.0, float(cap))) if cap else timeout


def completion_budget(requested: int) -> int:
    """The max_tokens actually sent to the model for a caller's requested answer length."""
    return min(MAX_COMPLETION_TOKENS, max(1, int(requested)) + REASONING_HEADROOM_TOKENS)


class LLMService:
    """
    Service for managing LLM interactions with retry logic.

    Replies are NOT cached by prompt: interview prompts carry the conversation so far and almost never
    repeat. Work whose input does repeat is cached where it happens (``app.services.content_cache``).
    """
    
    def __init__(self):
        """Initialize LLM service."""
        # Switches the content caches off (the interview harness does this, so a repeat run is a real run).
        self._cache_enabled = True
        self._rate_limiter = asyncio.Semaphore(max_concurrency())
    
    async def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        tier: Optional[str] = None,
        attempts: int = 3,
        timeout_cap: Optional[float] = None,
    ) -> str:
        """
        Invoke LLM with retry logic.

        Args:
            prompt: User prompt
            temperature: Temperature for generation (0.0-2.0)
            max_tokens: Maximum tokens to generate (default: 2048)
            system_prompt: System prompt to use
            tier: Model tier — "cheap" for extraction/formatting/classification,
                  "strong" (default) for reasoning/reflection/decisions. Pass
                  None to use the default strong chain.

        Returns:
            str: Generated response

        Raises:
            LLMServiceError: If LLM call fails
            LLMTimeoutError: If timeout occurs
            LLMRateLimitError: If rate limit is exceeded
        """
        # Use default max_tokens if not provided (avoid 65536 default)
        if max_tokens is None:
            max_tokens = 2048  # Reasonable limit for interview questions

        target_llm = get_llm(tier) if tier else llm

        if not await llm_budget.consume():
            raise LLMBudgetExceeded()

        # ``attempts``: whole-chain retries (plan step 10: 2 for calls made during an interview turn).
        max_retries = max(1, int(attempts or 3))

        async with self._rate_limiter:
            for attempt in range(max_retries):
                try:
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})

                    # temperature / max_tokens are MODEL parameters: they go as keyword arguments. They used
                    # to be put in LangChain's ``config`` (tags, callbacks, ...), which ignores them, so
                    # every call silently ran with the model's defaults (temperature 0.7, 2048 tokens).
                    response = await asyncio.wait_for(
                        target_llm.ainvoke(
                            messages, None, temperature=temperature, max_tokens=completion_budget(max_tokens),
                            timeout=request_timeout(max_tokens, timeout_cap),
                        ),
                        timeout=180
                    )

                    result_content = response.content

                    logger.info(f"Successfully generated response (attempt {attempt + 1}/{max_retries})")
                    return result_content

                except asyncio.TimeoutError:
                    logger.warning(f"LLM timeout on attempt {attempt + 1}/{max_retries}")
                    if attempt == max_retries - 1:
                        raise LLMTimeoutError(60)
                    continue

                except ValueError as e:
                    error_msg = str(e).lower()

                    if "402" in error_msg or "credit" in error_msg or "insufficient" in error_msg or "budget" in error_msg:
                        logger.error(f"Insufficient credits/budget (HTTP 402): {str(e)}")
                        raise LLMServiceError("Insufficient credits or budget. Please upgrade your API plan or reduce token usage.")

                    if "rate limit" in error_msg:
                        logger.warning(f"Rate limit detected on attempt {attempt + 1}/{max_retries}")
                        if attempt == max_retries - 1:
                            raise LLMRateLimitError(60, 60)
                        continue

                    raise LLMServiceError(f"LLM validation error: {str(e)}")

                except Exception as e:
                    logger.error(f"LLM error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                    if attempt == max_retries - 1:
                        raise LLMServiceError(f"LLM invocation failed after {max_retries} attempts: {str(e)}")
                    continue

        raise LLMServiceError("Unknown LLM error")

    async def invoke_stream(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        tier: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response token by token."""
        if max_tokens is None:
            max_tokens = 2048

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        target_llm = get_llm(tier) if tier else llm
        if not await llm_budget.consume():
            raise LLMBudgetExceeded()

        async with self._rate_limiter:
            async for token in target_llm.astream(
                messages, None, temperature=temperature, max_tokens=completion_budget(max_tokens),
                timeout=request_timeout(max_tokens),
            ):
                yield token
    
    async def invoke_structured(
        self,
        prompt: str,
        pydantic_model: Any,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        tier: Optional[str] = None
    ) -> Any:
        """
        Invoke LLM and parse structured output using Pydantic model.
        
        Args:
            prompt: User prompt
            pydantic_model: Pydantic model for output parsing
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            tier: Model tier (see ``invoke``)
            
        Returns:
            Pydantic model instance with parsed output
            
        Raises:
            LLMServiceError: If parsing or invocation fails
        """
        try:
            # For now, just use regular invoke and parse manually
            # Later can integrate with bedrock structured outputs or similar
            response = await self.invoke(
                prompt, temperature=temperature, max_tokens=max_tokens, tier=tier
            )
            
            # Try to parse as JSON first
            try:
                from app.intelligence._helpers import parse_json

                data = parse_json(response)
                return pydantic_model(**data)
            except (ValueError, TypeError):
                # Not JSON, return raw response
                logger.warning("LLM did not return structured JSON, using raw response")
                return pydantic_model(content=response)
                
        except Exception as e:
            logger.error(f"Structured invocation failed: {str(e)}")
            raise LLMServiceError(f"Failed to parse structured response: {str(e)}")
    
# Singleton instance
_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get LLM service singleton instance.
    
    Returns:
        LLMService: Singleton instance
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    
    return _llm_service_instance

