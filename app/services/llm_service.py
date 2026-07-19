"""
LLM Service with caching, retry logic, and prompt management.
Handles all LLM operations with proper error handling.
"""
import asyncio
import logging
import json
from typing import Any, Optional
from functools import wraps
import time

from app.models.llm import llm
from app.exceptions import LLMServiceError, LLMTimeoutError, LLMRateLimitError

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for managing LLM interactions with caching and retry logic.
    """
    
    def __init__(self):
        """Initialize LLM service."""
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._rate_limit_delay = 1.0  # Seconds between requests
    
    async def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Invoke LLM with caching support and retry logic.
        
        Args:
            prompt: User prompt
            temperature: Temperature for generation (0.0-2.0)
            max_tokens: Maximum tokens to generate (default: 2048)
            system_prompt: System prompt to use
            
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
        
        # Check cache first
        cache_key = self._generate_cache_key(prompt, temperature, system_prompt)
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if time.time() - cached_result['timestamp'] < self._cache_ttl:
                logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                return cached_result['content']
        
        # Exponential backoff retry
        max_retries = 3
        initial_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Respect rate limiting
                await asyncio.sleep(self._rate_limit_delay * (attempt if attempt > 0 else 1))
                
                # Build messages
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # Invoke LLM
                config = {
                    "temperature": temperature
                }
                if max_tokens:
                    config["max_tokens"] = max_tokens
                
                response = await llm.ainvoke(messages, config)
                
                result_content = response.content
                
                # Cache result
                self._cache[cache_key] = {
                    'content': result_content,
                    'timestamp': time.time()
                }
                
                logger.info(f"Successfully generated response (attempt {attempt + 1}/{max_retries})")
                return result_content
                
            except asyncio.TimeoutError:
                logger.warning(f"LLM timeout on attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    raise LLMTimeoutError(60)  # Assuming 60 second timeout
                continue
                
            except ValueError as e:
                error_msg = str(e).lower()
                
                # HTTP 402 errors (insufficient credits) should NOT be retried
                if "402" in error_msg or "credit" in error_msg or "insufficient" in error_msg or "budget" in error_msg:
                    logger.error(f"Insufficient credits/budget (HTTP 402): {str(e)}")
                    raise LLMServiceError("Insufficient credits or budget. Please upgrade your API plan or reduce token usage.")
                
                # Rate limit errors should be retried
                if "rate limit" in error_msg:
                    logger.warning(f"Rate limit detected on attempt {attempt + 1}/{max_retries}")
                    if attempt == max_retries - 1:
                        raise LLMRateLimitError(60, 60)  # Retry after 60 seconds
                    continue
                    
                # Other validation errors should not be retried
                raise LLMServiceError(f"LLM validation error: {str(e)}")
                
            except Exception as e:
                logger.error(f"LLM error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt == max_retries - 1:
                    raise LLMServiceError(f"LLM invocation failed after {max_retries} attempts: {str(e)}")
                continue
        
        # Should never reach here, but keep mypy happy
        raise LLMServiceError("Unknown LLM error")
    
    async def invoke_structured(
        self,
        prompt: str,
        pydantic_model: Any,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None
    ) -> Any:
        """
        Invoke LLM and parse structured output using Pydantic model.
        
        Args:
            prompt: User prompt
            pydantic_model: Pydantic model for output parsing
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Pydantic model instance with parsed output
            
        Raises:
            LLMServiceError: If parsing or invocation fails
        """
        try:
            # For now, just use regular invoke and parse manually
            # Later can integrate with bedrock structured outputs or similar
            response = await self.invoke(prompt, temperature=temperature, max_tokens=max_tokens)
            
            # Try to parse as JSON first
            try:
                # Extract JSON from response if it's wrapped in markdown code blocks
                if '```json' in response:
                    response = response.split('```json')[1].split('```')[0].strip()
                elif '```' in response:
                    response = response.split('```')[1].split('```')[0].strip()
                
                data = json.loads(response)
                return pydantic_model(**data)
            except json.JSONDecodeError:
                # Not JSON, return raw response
                logger.warning("LLM did not return structured JSON, using raw response")
                return pydantic_model(content=response)
                
        except Exception as e:
            logger.error(f"Structured invocation failed: {str(e)}")
            raise LLMServiceError(f"Failed to parse structured response: {str(e)}")
    
    def _generate_cache_key(self, prompt: str, temperature: float, system_prompt: Optional[str]) -> str:
        """
        Generate cache key from prompt and parameters.
        
        Args:
            prompt: User prompt
            temperature: Temperature parameter
            system_prompt: System prompt
            
        Returns:
            str: Cache key
        """
        # Simple cache key - should be replaced with proper hashing in production
        key_data = {
            "prompt": prompt,
            "temp": temperature
        }
        return str(hash(frozenset(key_data.items())))
    
    def clear_cache(self):
        """Clear the LLM response cache."""
        self._cache = {}
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