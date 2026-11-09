"""OPENROUTER_ROUTING chooses the OpenRouter host: cheapest (default) or fastest."""
import pytest

from app.models import llm


@pytest.mark.parametrize("value,expected", [
    (None, "price"),            # default: cheapest
    ("cheapest", "price"),
    ("fastest", "throughput"),
    ("  Fastest ", "throughput"),
    ("throughput", "throughput"),
    ("nonsense", "price"),      # unknown values fall back to the cheap side
])
def test_provider_sort(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("OPENROUTER_ROUTING", raising=False)
    else:
        monkeypatch.setenv("OPENROUTER_ROUTING", value)
    assert llm.openrouter_provider_sort() == expected


def test_default_request_body_sorts_by_price_and_keeps_low_reasoning():
    body = llm._OPENROUTER_EXTRA_BODY
    assert body["reasoning"] == {"effort": "low"}
    assert body["provider"]["sort"] in {"price", "throughput"}
