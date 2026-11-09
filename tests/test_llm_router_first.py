"""LLM_ROUTER_FIRST puts the local router at the front of both chains; by default it stays the last fallback."""
from app.models import llm


def test_router_is_last_fallback_by_default(monkeypatch):
    monkeypatch.delenv("LLM_ROUTER_FIRST", raising=False)
    monkeypatch.setattr(llm, "_ROUTER_MODEL", "fallback")
    strong, cheap = llm._chain_configs(False)
    assert strong[0]["model"] != "fallback"
    assert strong[-1]["model"] == "fallback"
    assert cheap[0]["model"] != "fallback"


def test_router_first_leads_both_chains(monkeypatch):
    monkeypatch.setenv("LLM_ROUTER_FIRST", "1")
    monkeypatch.setattr(llm, "_ROUTER_MODEL", "fallback")
    monkeypatch.setattr(llm, "_ROUTER_URL", "http://localhost:20128/v1")
    for free in (False, True):
        strong, cheap = llm._chain_configs(free)
        assert strong[0] == {"model": "fallback", "base_url": "http://localhost:20128/v1", "api_key": None}
        assert cheap[0] == strong[0]
        assert len(strong) > 1  # the other providers stay as backup
