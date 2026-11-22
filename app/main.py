from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import logging
import traceback
from app.api.interview_agent import router as interview_agent
from app.api.interview_ws import router as interview_ws_router
from app.api.v1.auth import router as auth_router
from app.api.v1.orgs import router as orgs_router
from app.api.v1.marketplace import router as marketplace_router
from app.api.v1.admin import router as admin_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.org_content import router as org_content_router
from app.api.v1.it import router as it_router
from app.api.v1.analytics import router as analytics_v1_router
from app.api.v1.public import router as public_router
from app.api.v1.scorecards import router as scorecards_router
from app.api.v1.candidate_ranking import router as candidate_ranking_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.system import router as system_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.demo import router as demo_router
from app.config import settings

API_VERSION = "v1"
logging.basicConfig(level=logging.INFO)
# The interview WebSocket carries its tokens in the URL query string and uvicorn logs the full URL.
from app.utils.log_redaction import install_url_secret_redaction

install_url_secret_redaction()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    # Startup: verify async SQLAlchemy engine is ready (the slow first connection is warmed in the background below)
    from app.database.session import get_engine
    eng = get_engine()
    if eng:
        logger.info("Async SQLAlchemy engine ready")
    else:
        logger.warning("DATABASE_URL not set — async DB features disabled")

    # Startup: initialize Redis cache
    from app.services.cache import get_cache
    await get_cache().init()

    # Pre-load prompt templates into cache
    from app.services.prompt_loader import load_prompt as _warm
    _warm("interview", "question_generation.md", job_role="warmup", phase="intro", difficulty_level=1,
          company_context="N/A", candidate_profile="N/A", question_number=0, conversation_history="(warmup)")
    logger.info("Prompt cache pre-warmed")

    # Start WebSocket stale-connection cleanup
    from app.api.interview_ws import start_cleanup_task
    cleanup_handle = start_cleanup_task()

    async def _warm_up():
        """Slow, best-effort warm-up that runs AFTER the server is listening.

        uvicorn opens its port only when this startup function yields, and hosts such as Render give up on a
        service that has not opened a port within a few minutes. A remote database connect can take ~30 s and loading
        the embedding model more than a minute on a small CPU, so none of it may block startup. A request that needs
        one of these before it is ready simply pays for it, exactly as when the warm-up is skipped.
        """
        if eng:
            # Open the first connection now: against a remote database it takes several seconds.
            try:
                from sqlalchemy import text

                async def _warm_db():
                    async with eng.connect() as conn:
                        await conn.execute(text("select 1"))

                await asyncio.wait_for(_warm_db(), timeout=30.0)
                logger.info("Database connection pool warmed up")

                # Evaluations interrupted by the previous shutdown would otherwise stay "pending" forever.
                from app.marketplace.fit_evaluation import resume_unfinished_evaluations

                app.state.resume_evaluations_task = asyncio.create_task(resume_unfinished_evaluations())
            except Exception as exc:  # noqa: BLE001 - never let this affect the app
                logger.warning(f"Database warm-up skipped: {exc}")

        # Embedding backend + Pinecone client: the first RAG retrieval otherwise loads the model inside the request,
        # which can exceed the retrieval timeout and produce an empty company brain.
        try:
            from app.rag.embeddings import hosted_backend_selected
            from app.rag.pinecone_store import get_embedding, get_pinecone_client

            def _warm_embeddings():
                get_pinecone_client()
                get_embedding().embed_query("warmup company overview retrieval")

            await asyncio.wait_for(
                asyncio.to_thread(_warm_embeddings), timeout=60.0 if hosted_backend_selected() else 180.0
            )
            logger.info("Embedding backend + Pinecone client warmed up")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Embedding/Pinecone warm-up failed (best-effort): {exc}")

    app.state.warmup_task = asyncio.create_task(_warm_up())

    # Daily delete of refresh tokens that expired more than a week ago (rotation only marks them revoked).
    from app.auth.token_cleanup import cleanup_loop
    app.state.token_cleanup_task = asyncio.create_task(cleanup_loop()) if eng else None

    yield

    token_cleanup = getattr(app.state, "token_cleanup_task", None)
    if token_cleanup is not None:
        token_cleanup.cancel()

    # Shutdown: stop the warm-up if it is still running
    warmup = getattr(app.state, "warmup_task", None)
    if warmup is not None and not warmup.done():
        warmup.cancel()
        try:
            await warmup
        except BaseException:  # noqa: BLE001 - cancellation or a late failure must not block shutdown
            pass

    # Shutdown: flush v4 session store (drains dirty sessions / closes Redis client)
    from app.services.v4_session_store import get_v4_session_store
    store = get_v4_session_store()
    store.flush()
    if hasattr(store, "close"):
        store.close()
    logger.info("v4 session store flushed")

    # Shutdown: dispose async engine
    if eng:
        await eng.dispose()
        logger.info("Async SQLAlchemy engine disposed")

    # Shutdown: close Redis connection
    from app.services.cache import get_cache
    await get_cache().close()


def docs_urls(enabled: bool) -> dict:
    """FastAPI settings for the interactive docs; None turns a URL off (the route then answers 404)."""
    return {
        "docs_url": "/docs" if enabled else None,
        "redoc_url": "/redoc" if enabled else None,
        "openapi_url": "/openapi.json" if enabled else None,
    }


app = FastAPI(lifespan=lifespan, **docs_urls(settings.api_docs_enabled))
app.include_router(interview_agent)
app.include_router(interview_ws_router)

# v1 API routes
app.include_router(auth_router, prefix=f"/api/{API_VERSION}")
app.include_router(orgs_router, prefix=f"/api/{API_VERSION}")
app.include_router(marketplace_router, prefix=f"/api/{API_VERSION}")
app.include_router(admin_router, prefix=f"/api/{API_VERSION}")
app.include_router(candidates_router, prefix=f"/api/{API_VERSION}")
app.include_router(invitations_router, prefix=f"/api/{API_VERSION}")
app.include_router(org_content_router, prefix=f"/api/{API_VERSION}")
app.include_router(it_router, prefix=f"/api/{API_VERSION}")
app.include_router(analytics_v1_router, prefix=f"/api/{API_VERSION}")
app.include_router(public_router, prefix=f"/api/{API_VERSION}")
app.include_router(scorecards_router, prefix=f"/api/{API_VERSION}")
app.include_router(candidate_ranking_router, prefix=f"/api/{API_VERSION}")
app.include_router(audit_logs_router, prefix=f"/api/{API_VERSION}")
app.include_router(intelligence_router, prefix=f"/api/{API_VERSION}")
app.include_router(demo_router, prefix=f"/api/{API_VERSION}")
app.include_router(system_router)


# ✅ Custom middleware to handle ngrok-specific headers
from starlette.datastructures import MutableHeaders
from app.middleware.rate_limit import RateLimitMiddleware


class NgrokMiddleware:
    """Adds the ngrok header to every HTTP response.

    Plain ASGI on purpose: ``BaseHTTPMiddleware`` delays the end of the response until
    FastAPI background tasks (fit evaluation, emails, document ingestion) have finished.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_header(message):
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["ngrok-skip-browser-warning"] = "true"
            await send(message)

        await self.app(scope, receive, send_with_header)


# Innermost middleware (runs first)
app.add_middleware(NgrokMiddleware)

# Strict rate limit on auth endpoints (20 req/min per IP)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=20,
    window_seconds=60,
    paths=["/api/v1/candidates/login", "/api/v1/candidates/register",
           "/api/v1/candidates/auth/refresh",
           "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh",
           "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password",
           "/api/v1/candidates/forgot-password", "/api/v1/candidates/reset-password",
           "/api/v1/candidates/send-verification",
           "/api/v1/candidates/claim", "/api/v1/candidates/verify"],
    trusted_proxies=settings.TRUSTED_PROXY_COUNT,
)

# General rate limit on all API + v4 endpoints (120 req/min per IP)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=120,
    window_seconds=60,
    paths=["/api/v1/", "/interviews/", "/"],
    trusted_proxies=settings.TRUSTED_PROXY_COUNT,
)

# CORS must be OUTERMOST so it intercepts OPTIONS preflight before other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # Local development: Vite may fall back to another port, and localhost and
    # 127.0.0.1 are different origins. Accept any loopback origin so a dev
    # server on :3001 or http://127.0.0.1:3000 can still call the API.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}")
    logger.error(traceback.format_exc())
    is_dev = "localhost" in settings.APP_URL or "127.0.0.1" in settings.APP_URL
    detail = f"Internal server error: {type(exc).__name__}: {exc}" if is_dev else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


@app.get("/")
def home():
    return {"status": "AI Interview Agent Running"}


@app.get("/health")
@app.post("/health")
def health_check():
    return {
        "status": "✅ API is working",
        "message": "You can now access the API from your HTML file",
        "timestamp": str(__import__('datetime').datetime.now()),
        "cors": "✅ CORS enabled"
    }
