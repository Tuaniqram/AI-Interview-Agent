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
    get_question_workflow()
    get_evaluation_workflow()
    logger.info("LangGraph workflows pre-warmed")

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


# ✅ CORS Configuration - Must be FIRST middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

app.add_middleware(NgrokMiddleware)

# Rate limiting on auth + public endpoints (60 req/min per IP)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=60,
    window_seconds=60,
    paths=["/api/v1/candidates/login", "/api/v1/candidates/register",
           "/api/v1/auth/login", "/api/v1/auth/register",
           "/api/v1/public/"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
    )


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

