from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import logging
import traceback
from app.api.interview_agent import router as interview_agent
from app.api.interview_ws import router as interview_ws_router
from app.api.avatar_ws import router as avatar_ws_router
from app.api.v1.auth import router as auth_router
from app.api.v1.orgs import router as orgs_router
from app.api.v1.marketplace import router as marketplace_router
from app.api.v1.scheduling import router as scheduling_router
from app.api.v1.admin import router as admin_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.departments import router as departments_v1_router
from app.api.v1.analytics import router as analytics_v1_router
from app.api.v1.public import router as public_router
from app.api.v1.scorecards import router as scorecards_router
from app.api.v1.candidate_ranking import router as candidate_ranking_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.system import router as system_router
from app.api.interview_v4 import router as interview_v4_router
from app.config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify async SQLAlchemy engine is ready
    from app.database.session import get_engine
    eng = get_engine()
    if eng:
        logger.info("Async SQLAlchemy engine ready")
    else:
        logger.warning("DATABASE_URL not set — async DB features disabled")

    # Startup: initialize Redis cache
    from app.services.cache import get_cache
    await get_cache().init()

    # Pre-warm LangGraph workflows to avoid first-request compilation cost
    from app.graph.question_workflow import get_question_workflow
    from app.graph.evaluation_workflow import get_evaluation_workflow
    from app.graph.interview_graph import build_interview_graph
    get_question_workflow()
    get_evaluation_workflow()
    build_interview_graph()
    logger.info("LangGraph workflows pre-warmed (v3 + v4)")

    # Pre-load prompt templates into cache
    from app.services.prompt_loader import load_prompt as _warm
    _warm("system", "interviewer_system.md")
    _warm("system", "followup_system.md")
    _warm("system", "evaluator_system.md")
    _warm("interview", "question_generation.md", job_role="warmup", phase="intro", difficulty_level=1,
          department_context="N/A", candidate_profile="N/A", question_number=0, conversation_history="(warmup)")
    logger.info("Prompt cache pre-warmed")

    # Start WebSocket stale-connection cleanup
    from app.api.interview_ws import start_cleanup_task
    cleanup_handle = start_cleanup_task()

    yield

    # Shutdown: flush v4 session store to disk
    from app.services.v4_session_store import get_v4_session_store
    get_v4_session_store().flush()
    logger.info("v4 session store flushed")

    # Shutdown: dispose async engine
    if eng:
        await eng.dispose()
        logger.info("Async SQLAlchemy engine disposed")

    # Shutdown: close Redis connection
    from app.services.cache import get_cache
    await get_cache().close()


app = FastAPI(lifespan=lifespan)
app.include_router(interview_agent)
app.include_router(avatar_ws_router)
app.include_router(interview_ws_router)

# v1 API routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(orgs_router, prefix="/api/v1")
app.include_router(marketplace_router, prefix="/api/v1")
app.include_router(scheduling_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(candidates_router, prefix="/api/v1")
app.include_router(invitations_router, prefix="/api/v1")
app.include_router(departments_v1_router, prefix="/api/v1")
app.include_router(analytics_v1_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(scorecards_router, prefix="/api/v1")
app.include_router(candidate_ranking_router, prefix="/api/v1")
app.include_router(audit_logs_router, prefix="/api/v1")
app.include_router(system_router)
app.include_router(interview_v4_router)


# ✅ CORS Configuration - Must be FIRST middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ✅ Custom middleware to handle ngrok-specific headers
from starlette.middleware.base import BaseHTTPMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

class NgrokMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response

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
           "/api/v1/candidates/send-verification"],
)

# General rate limit on all API + v4 endpoints (120 req/min per IP)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=120,
    window_seconds=60,
    paths=["/api/v1/", "/interviews/", "/"],
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


@app.options("/health")
async def health_options():
    return {"status": "ok"}


@app.options("/{full_path:path}")
async def preflight(full_path: str):
    return {"status": "ok"}

