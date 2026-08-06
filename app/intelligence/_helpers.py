"""Shared private helpers for the intelligence module."""
import json
import logging

logger = logging.getLogger(__name__)


async def parse_llm_json_with_retry(
    llm_service,
    prompt: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 900,
    tier: str = "cheap",
):
    """Invoke the LLM and parse its JSON; retry once with a larger budget.

    Cheap tiers frequently truncate long JSON answers mid-object (no closing
    brace, so no parser can recover). A single retry with a bigger token
    budget returns the complete object; if it still fails the original parse
    error propagates and callers fall back to their deterministic path.
    """
    response = await llm_service.invoke(
        prompt=prompt, temperature=temperature, max_tokens=max_tokens, tier=tier
    )
    try:
        return parse_json(response)
    except ValueError as first_error:
        response = await llm_service.invoke(
            prompt=prompt, temperature=temperature, max_tokens=max_tokens * 2, tier=tier
        )
        try:
            return parse_json(response)
        except ValueError:
            raise first_error from None


def parse_json(response: str) -> dict:
    """Parse an LLM JSON response, tolerating markdown code fences, trailing
    prose after the object, and prose *before* the object (cheap tiers answer
    "Here is the JSON:" first). Raises ``ValueError`` when no JSON object is
    present — callers treat that as "use heuristics".
    """
    content = (response or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        content = content.rsplit("```", 1)[0]
    content = content.strip()

    try:
        data, _ = json.JSONDecoder().raw_decode(content)
        if not isinstance(data, dict):
            raise ValueError("LLM response was not a JSON object")
        return data
    except (ValueError, json.JSONDecodeError):
        pass

    start = content.find("{")
    if start != -1:
        try:
            data, _ = json.JSONDecoder().raw_decode(content[start:])
            if isinstance(data, dict):
                return data
        except (ValueError, json.JSONDecodeError):
            pass

    raise ValueError(f"no JSON object in LLM response: {content[:120]!r}")


def dedupe(items) -> list:
    """Preserve-order de-duplication that drops blanks and dupes."""
    seen = set()
    out = []
    for item in items or []:
        key = str(item).strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out
