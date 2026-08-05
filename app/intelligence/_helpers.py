"""Shared private helpers for the intelligence module."""
import json
import logging

logger = logging.getLogger(__name__)


def parse_json(response: str) -> dict:
    """Parse an LLM JSON response, tolerating markdown code fences."""
    content = (response or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        content = content.rsplit("```", 1)[0]
    content = content.strip()
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("LLM response was not a JSON object")
    return data


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
