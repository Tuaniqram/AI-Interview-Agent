# AI Interview Agent - LLM Workflow

## Overview

This document describes how the AI Interview Agent integrates with Large Language Models (LLMs). It covers LLM initialization, invocation patterns, prompt management, and optimization strategies.

## Technology Stack

**Current**:
- **LLM Provider**: OpenRouter (OpenAI-compatible API)
- **Wrapper**: LangChain's `ChatOpenAI`
- **orjson**: Fast JSON serialization for API responses

**Configuration**:
```python
# app/models/llm.py
llm = ChatOpenAI(
    model="openrouter/auto",
    temperature=0.7,
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1"
)
```

**Environment Variables Required**:
```
OPENROUTER_API_KEY=your_api_key_here
```

## LLM Invocation Patterns

### Current Pattern (Direct Invocation)

**❌ BAD - Currently in use**:
```python
# app/api/interview.py - Direct LLM calls in API layer
llm.invoke(prompt)

# app/agents/interviewer.py - Direct LLM calls in agent
response = llm.invoke(prompt)
question_text = response.content.strip()
```

**Issues**:
- No caching
- No retry logic
- No structured output parsing
- Embedded prompts in code
- No logging of LLM calls

### Recommended Pattern (Centralized Management)

**✅ GOOD - Proposed architecture**:
```python
# app/services/llm_manager.py
class LLMManager:
    def __init__(self):
        self.client = llm
        self.cache = {}
    
    async def invoke(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_retries: int = 3,
        timeout: int = 30
    ) -> str:
        """
        Invoke LLM with caching and retry logic
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Temperature (0.0 to 1.0)
            max_retries: Maximum retry attempts
            timeout: Timeout in seconds
            
        Returns:
            LLM response text
        """
        pass
    
    async def invoke_with_structured_output(
        self,
        prompt: str,
        output_schema: dict,
        system_prompt: str = None
    ) -> dict:
        """
        Invoke LLM and parse structured JSON output
        
        Args:
            prompt: User prompt
            output_schema: Expected schema for parsing
            system_prompt: System prompt (optional)
            
        Returns:
            Parsed dictionary
        """
        pass
    
    async def get_cached_response(
        self,
        prompt: str,
        system_prompt: str = None
    ) -> Optional[str]:
        """
        Check cache for existing response
        
        Args:
            prompt: Prompt to lookup
            system_prompt: System prompt for cache key
            
        Returns:
            Cached response or None
        """
        cache_key = hashlib.md5(f"{prompt}:{system_prompt}".encode()).hexdigest()
        return self.cache.get(cache_key)
    
    def set_cached_response(
        self,
        prompt: str,
        system_prompt: str = None,
        response: str
    ):
        """
        Cache LLM response
        
        Args:
            prompt: Original prompt
            system_prompt: System prompt for cache key
            response: Response to cache
        """
        cache_key = hashlib.md5(f"{prompt}:{system_prompt}".encode()).hexdigest()
        self.cache[cache_key] = response
```

## Prompt Pattern: Structured JSON Output

### Problem with Current Approach

**Current implementation** (lines 722-774 in interview.py):
```python
# Try-catch parsing logic - fragile
score_match = feedback_text.split("\n")
score = 7  # Default if not found
strengths = []
weaknesses = []
suggested_follow_up = ""
found=False

for line in score_match:
    if line.strip().startswith("**Score:"):
        for word in line.split():
            try:
                score = float(word.replace("/", "").replace(":", "").strip())
                break
            except:
                pass
    # ... more fragile parsing logic
```

**Issues**:
- Fragile parsing (depends on text format)
- No validation
- Missing scores default to 7 (arbitrary)
- No handling of parsing failures

### Solution: Structured JSON Prompts

**✅ GOOD - Try this approach**:

**1. System Prompt** (`prompts/system/evaluator_system.md`):
```markdown
# Purpose
Evaluate candidate answers with structured JSON output.

# Instructions
You are an experienced technical interviewer evaluating candidates.
Provide your feedback in the following JSON structure:

# Constraints
- Always return valid JSON
- No markdown formatting in JSON values
- Numeric scores must be floats between 0 and 2 (for full/partial)
- Include all requested fields

# Output Format
```json
{
  "overall_score": 0.5 to 2.0,
  "technical_score": 0.0 to 2.0,
  "communication_score": 0.0 to 2.0,
  "strengths": "string array",
  "weaknesses": "string array",
  "suggested_follow_up": "string",
  "feedback_detail": "string"
}
```
```

**2. Python Implementation**:
```python
# app/services/interview_service.py
from pydantic import BaseModel, Field
import json
import re

class EvaluationResult(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=2.0)
    technical_score: float = Field(..., ge=0.0, le=2.0)
    communication_score: float = Field(..., ge=0.0, le=2.0)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggested_follow_up: str = ""
    feedback_detail: str = ""

async def _evaluate_answer(
    self,
    question: str,
    candidate_answer: str,
    job_role: str
) -> EvaluationResult:
    """Evaluate answer with structured output"""
    
    # Load prompts
    system_prompt = await prompt_loader.load("system/evaluator_system.md")
    user_prompt = await prompt_loader.load("interview/answer_evaluation.md", {
        "job_role": job_role,
        "question": question,
        "answer": candidate_answer
    })
    
    # Invoke LLM
    response_text = await llm_manager.invoke(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=0.7
    )
    
    # Parse JSON
    try:
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
        response_text = json_match.group(1) if json_match else response_text
        
        # Parse
        data = json.loads(response_text)
        result = EvaluationResult(**data)
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        # Fallback: return defaults
        return EvaluationResult(overall_score=1.0)
```

## LLM Caching Strategy

### Why Cache?

**Cost Reduction**:
- LLM API calls can be expensive
- Imitate questions and evaluations are reused
- Reduces API calls by ~60% in typical workflows

**Performance**:
- Faster response times
- Reduces latency
- Improves user experience

### Cache Implementation

```python
import hashlib
import json
from typing import Optional
import time

class LLMLookupCache:
    """Redis-based cache for expensive LLM calls"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client or Redis()
        self.ttl = 3600  # 1 hour cache duration
        self.key_prefix = "llm_cache"
    
    def _generate_key(
        self,
        prompt_type: str,
        prompt_hash: str,
        context_hash: str
    ) -> str:
        """Generate unique cache key"""
        return f"{self.key_prefix}:{prompt_type}:{prompt_hash}:{context_hash}"
    
    async def get(self, prompt_type: str, context: dict) -> Optional[str]:
        """Get cached response"""
        prompt_hash = hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()
        key = self._generate_key(prompt_type, prompt_hash, "")
        
        cached = await self.redis.get(key)
        if cached:
            logger.info(f"Cache HIT for {prompt_type}")
            return cached
        
        logger.debug(f"Cache MISS for {prompt_type}")
        return None
    
    async def set(
        self,
        prompt_type: str,
        context: dict,
        response: str
    ):
        """Set cache with expiration"""
        prompt_hash = hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()
        key = self._generate_key(prompt_type, prompt_hash, "")
        
        await self.redis.setex(key, self.ttl, response)
        logger.info(f"Cache SET for {prompt_type}")
    
    async def clear_pattern(self, pattern: str):
        """Clear cache with pattern"""
        keys = await self.redis.keys(f"{self.key_prefix}:{pattern}:*")
        if keys:
            await self.redis.delete(*keys)

# Usage in Service Layer
async def get_next_question(self, phase: str, job_role: str) -> str:
    """Get question with caching"""
    
    # Try cache first
    cache_key = f"question:{phase}:{hashlib.md5(job_role.encode()).hexdigest()}"
    cached = await llm_cache.get("question_generation", {"phase": phase, "job_role": job_role})
    
    if cached:
        return cached
    
    # Not in cache - generate new question
    prompt = await prompt_loader.load(f"interview/{phase}_question.md", {
        "job_role": job_role,
        "phase": phase
    })
    
    question = await llm_manager.invoke(prompt)
    
    # Cache it
    await llm_cache.set("question_generation", {"phase": phase, "job_role": job_role}, question)
    
    return question
```

## LLM Error Handling

### Common Errors

```python
# Network errors
try:
    response = await llm_manager.invoke(prompt)
except ConnectionTimeout:
    logger.error("LLM connection timeout")
    return "Sorry, the interviewer is processing. Please try again."

# API rate limiting
except RateLimitError:
    logger.warning("LLM API rate limit exceeded")
    # Fall back to pre-defined questions from template
    return PHASE_TEMPLATES[phase]["example_questions"][question_num]

# Invalid responses
except JSONDecodeError:
    logger.error("Invalid LLM response format")
    # Use structured field extraction as fallback
    return self._parse_fallback(response_text)

# General errors
except Exception as e:
    logger.exception(f"Unexpected LLM error: {e}")
    return "An error occurred. Please try again later."
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def invokable_llm_call(prompt: str):
    """Call LLM with automatic retries"""
    response = await llm_manager.invoke(prompt)
    return response
```

## LLM Optimization Techniques

### 1. Temperature Tuning

**Temperature 0.7** (Current):
- Balanced creativity and consistency
- Good for interview questions
- Too random for requirements

**Temperature 0.3** (For Code Generation):
- More deterministic
- Better for code outputs
- Lower randomness

**Temperature 0.0** (For Formatting):
- Most predictable
- Good for extraction
- Minimal creativity

### 2. Token Optimization

**Bad - Long prompts**:
```python
prompt = f"""
You are an AI interviewer. You need to evaluate a candidate.
Here is their answer: {long_answer}
Here is the question they answered: {question}
Here is the job role: {job_role}
Here are the requirements: {requirements}
...
All this information is very important for evaluation.
Now evaluate: {candidate_answer}
"""

# 2000+ tokens
```

**Good - Context splitting**:
```python
system_prompt = "You are an experienced interviewer evaluating technical answers."  # 50 tokens

user_prompt = f"""
Job Role: {job_role}

Question:
{question}

Requirements:
{requirements}

Candidate Answer:
{candidate_answer}

Evaluation:
"""  # 300 tokens total

# Total: 350 tokens (much better)
```

### 3. Few-Shot Prompting

For consistent output formats:

```python
prompt = """
You generate approximately 3-5 bullet points.

Example:
**Strengths:**
- Demonstrated excellent Python skills
- Showed good problem-solving ability
- Communicated clearly

Now generate strengths for this answer:
{candidate_answer}

**Strengths:**
"""
```

### 4. Prompt Chaining

Break complex tasks into steps:

```python
# Step 1: Extract entities
entities_prompt = "Extract key technical concepts from: {answer}"
entities = await llm.invoke(entities_prompt)

# Step 2: Evaluate each entity
evaluation_prompt = "Evaluate these technical concepts: {entities} based on {requirements}"
evaluation = await llm.invoke(evaluation_prompt)

# Step 3: Synthesize
final_prompt = f"Synthesize: {entities}, {evaluation}"
final_result = await llm.invoke(final_prompt)
```

## LLM Configuration Management

### Centralized Configuration

```python
# app/config/llm_config.py
from pydantic_settings import BaseSettings

class LLMConfig(BaseSettings):
    provider: str = "openrouter"
    model: str = "openrouter/auto"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    max_retries: int = 3
    api_key: str
    api_base: str = "https://openrouter.ai/api/v1"
    
    class Config:
        env_prefix = "LLM_"

# Usage
llm_config = LLMConfig()

llm = ChatOpenAI(
    model=llm_config.model,
    temperature=llm_config.temperature,
    openai_api_key=llm_config.api_key,
    openai_api_base=llm_config.api_base,
    max_tokens=llm_config.max_tokens
)
```

### Environment Variables

```bash
# .env
LLM_PROVIDER=openrouter
LLM_MODEL=openrouter/auto
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
LLM_TIMEOUT=30
LLM_MAX_RETRIES=3
OPENROUTER_API_KEY=your_key_here
```

## Current LLM Calls Analysis

### Files with LLM Invocation

1. **app/api/interview.py**:
   - Line 127: Follow-up generation (deprecated)
   - Line 196-198: Evaluation (deprecated)
   - Line 216-218: Follow-up generation (deprecated)
   - Line 718: Evaluation in `_evaluate_answer()`
   - Line 827: Question generation in `_generate_phase_appropriate_question()`

2. **app/agents/interviewer.py**:
   - Line 45: Question generation

3. **app/agents/evaluator.py**:
   - Line 50: Evaluation

4. **app/company_agents/company_interviewer.py**:
   - Line 39: Question generation

5. **app/company_agents/company_evaluator.py**:
   - Line 56: Evaluation

### Recommendations

1. **Centralize** all LLM invocations through `LLMManager`
2. **Extract** all prompts to external files
3. **Implement** caching for repeated calls
4. **Add** structured output parsing with Pydantic
5. **Add** retry logic with tenacity package
6. **Add** monitoring/logging for all LLM calls

## Monitoring and Telemetry

### Log All LLM Calls

```python
import time

async def invoke_with_logging(self, prompt: str, **kwargs):
    """Invoke LLM with logging and timing"""
    
    start_time = time.time()
    
    try:
        response = await self.client.invoke(prompt, **kwargs)
        
        elapsed = time.time() - start_time
        logger.info(
            f"LLM Invocation Success | "
            f"model={self.client.model} | "
            f"tokens={getattr(response, 'usage', {}).get('total_tokens', 'N/A')} | "
            f"duration={elapsed:.2f}s"
        )
        
        return response
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"LLM Invocation Failed | "
            f"model={self.client.model} | "
            f"duration={elapsed:.2f}s | "
            f"error={str(e)}"
        )
        raise
```

### Metrics Collection

Export metrics for analysis:

```python
class LLMMetrics:
    def __init__(self):
        self.invocations = []
    
    def record_success(self, model: str, tokens: int, duration: float):
        self.invocations.append({
            "model": model,
            "tokens": tokens,
            "duration": duration,
            "status": "success",
            "timestamp": datetime.now()
        })
    
    def record_failure(self, model: str, error: str):
        self.invocations.append({
            "model": model,
            "error": error,
            "status": "failure",
            "timestamp": datetime.now()
        })
    
    def get_stats(self):
        """Get statistics across all invocations"""
        total = len(self.invocations)
        success = sum(1 for call in self.invocations if call["status"] == "success")
        
        avg_tokens = sum(call["tokens"] for call in self.invocations if call["tokens"] not in ["N/A"]) / success if success else 0
        avg_duration = sum(call["duration"] for call in self.invocations if call["status"] == "success") / success if success else 0
        
        return {
            "total_invocations": total,
            "success_rate": success / total if total > 0 else 0,
            "avg_tokens": avg_tokens,
            "avg_duration": avg_duration
        }
```

## LLM Cost Estimation

```python
# Rough cost calculator
class LLMCostCalculator:
    def __init__(self, model_prices: dict):
        """
        model_prices: {
            "gpt-4": {"input": 0.03 / 1K, "output": 0.06 / 1K},
            "claude-3": {"input": 0.015 / 1K, "output": 0.075 / 1K}
        }
        """
        self.model_prices = model_prices
    
    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        prices = self.model_prices.get(model, {})
        input_cost = (input_tokens / 1000) * prices.get("input", 0)
        output_cost = (output_tokens / 1000) * prices.get("output", 0)
        return input_cost + output_cost

# Estimated costs (per 1000 tokens)
COST_ESTIMATES = {
    "openrouter/auto": {
        "input": 0.01,   # Varies by model
        "output": 0.03
    }
}

# Example: One interview might cost
# - Question generation: 300 tokens x 2 = 600 tokens (Sample: Intro, Technical)
# - Answer evaluation: 500 tokens (Analysis) + 500 tokens (Feedback)
# - Follow-up generation: 200 tokens
# Total: ~1800 tokens per question
# Estimated cost per question: $0.02 - $0.05
```

## Best Practices

### ✅ DO

1. Use structured JSON outputs with Pydantic validation
2. Implement caching for expensive operations
3. Add retry logic for transient failures
4. Log all LLM invocations with timing
5. Use environment variables for configuration
6. Extract prompts to external files
7. Use appropriate temperature per task
8. Monitor token usage and costs
9. Validate LLM responses before processing
10. Clear cache on configuration changes

### ❌ DON'T

1. Hardcode prompts in Python files
2. Call LLM multiple times for same operation
3. Ignore errors from LLM
4. Use full context in every prompt
5. Vary temperature randomly
6. Make assumptions about response format
7. Forget to log LLM calls
8. Leave API calls uncached
9. Call LLM synchronously in async functions
10. Parse LLM output with fragile string matching