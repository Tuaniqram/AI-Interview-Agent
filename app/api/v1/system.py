from fastapi import APIRouter

router = APIRouter(tags=["system"])


# ── Health ──


@router.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "app": "AI Interview Agent",
        "version": "2.0.0",
    }


# ── LLM provider list (shared with the admin dashboard) ──

_HOSTS = (("openrouter.ai", "OpenRouter"), ("api.groq.com", "Groq"), ("localhost", "Local router"), ("127.0.0.1", "Local router"))


def llm_provider_status(configs: list[dict]) -> list[dict]:
    """The providers the app really calls, in chain order, from the live model chain (not a fixed list)."""
    out: list[dict] = []
    for cfg in configs:
        url = str(cfg.get("base_url") or "")
        host = next((name for needle, name in _HOSTS if needle in url), url or "Unknown")
        local = host == "Local router"
        out.append({
            "name": f"{host} ({cfg.get('model')})",
            # A local router needs no key; a hosted provider is usable only with one.
            "configured": True if local else bool(cfg.get("api_key")),
        })
    return out
