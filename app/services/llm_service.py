"""
LLM Service with caching, retry logic, and prompt management.
Handles all LLM operations with proper error handling.
"""
import asyncio
import logging
from typing import Any, AsyncGenerator, Optional
from functools import wraps
import time
import hashlib

from app.models.llm import llm, get_llm
from app.exceptions import LLMServiceError, LLMTimeoutError, LLMRateLimitError
from app.services.cache import get_cache

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


def request_timeout(requested: int) -> float:
    """Per-request timeout in seconds for a call that asks for ``requested`` tokens of answer."""
    return float(min(MAX_REQUEST_TIMEOUT_S, max(MIN_REQUEST_TIMEOUT_S, 20 + (max(1, int(requested)) + 400) / 40)))


def completion_budget(requested: int) -> int:
    """The max_tokens actually sent to the model for a caller's requested answer length."""
    return min(MAX_COMPLETION_TOKENS, max(1, int(requested)) + REASONING_HEADROOM_TOKENS)


class LLMService:
    """
    Service for managing LLM interactions with caching and retry logic.
    """
    
    def __init__(self):
        """Initialize LLM service."""
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_enabled = True
        self._rate_limiter = asyncio.Semaphore(3)
    
    async def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        tier: Optional[str] = None
    ) -> str:
        """
        Invoke LLM with caching support and retry logic.

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
        cache_key = self._generate_cache_key(prompt, temperature, system_prompt, tier)

        # Check Redis first. ``_cache_enabled = False`` turns BOTH caches off (the interview harness does this:
        # a repeat interview starts from identical prompts and would otherwise replay the first run).
        redis_cache = get_cache()
        use_cache = self._cache_enabled
        if use_cache and redis_cache.is_enabled:
            try:
                redis_val = await redis_cache.get(cache_key)
                if redis_val is not None:
                    logger.debug(f"Redis cache hit for prompt: {prompt[:50]}...")
                    return redis_val
            except Exception:
                pass

        # Fallback to in-memory cache
        if use_cache and cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if time.time() - cached_result['timestamp'] < self._cache_ttl:
                logger.debug(f"Memory cache hit for prompt: {prompt[:50]}...")
                return cached_result['content']
        
        max_retries = 3

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
                            timeout=request_timeout(max_tokens),
                        ),
                        timeout=180
                    )

                    result_content = response.content

                    if use_cache:
                        self._cache[cache_key] = {
                            'content': result_content,
                            'timestamp': time.time()
                        }

                    # Write to Redis cache (async, best-effort)
                    if use_cache and redis_cache.is_enabled:
                        try:
                            await redis_cache.set(cache_key, result_content, self._cache_ttl)
                        except Exception:
                            pass

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
    
    def _generate_cache_key(
        self,
        prompt: str,
        temperature: float,
        system_prompt: Optional[str],
        tier: Optional[str] = None
    ) -> str:
        raw = f"{prompt}|{temperature}|{system_prompt or ''}|{tier or 'strong'}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    async def clear_cache(self):
        """Clear the LLM response cache."""
        self._cache = {}
        redis_cache = get_cache()
        if redis_cache.is_enabled:
            try:
                pass
            except Exception:
                pass
        logger.info("LLM cache cleared")
    
    def get_cache_info(self) -> dict[str, int]:
        """
        Get information about the cache.
        
        Returns:
            dict: Cache size and other metrics
        """
        return {
            "size": len(self._cache),
            "ttl_seconds": self._cache_ttl
        }


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


# Convenience decorator for caching
def with_llm_cache(ttl: int = 300):
    """
    Decorator to cache LLM method results.
    
    Args:
        ttl: Time to live in seconds
    """
    def decorator(func):
        cache = {}
        
        @wraps(func)
        async def wrapper(self, prompt: str, *args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{prompt[:100]}"
            
            # Check cache
            if cache_key in cache:
                if time.time() - cache[cache_key]['timestamp'] < ttl:
                    logger.debug(f"Cached result for {func.__name__}")
                    return cache[cache_key]['result']
            
            # Call function
            result = await func(self, prompt, *args, **kwargs)
            
            # Cache result
            cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            return result
        
        return wrapper
    return decorator