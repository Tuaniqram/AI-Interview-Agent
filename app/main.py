from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging
from app.api.company import router as company_router
from app.api.knowledge import router as knowledge_router
from app.api.interview_agent import router as interview_agent
from app.api.interview_ws import router as interview_ws_router
from app.api.avatar_ws import router as avatar_ws_router
from app.api.templates import router as templates_router
from app.api.analytics import router as analytics_router

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
          company_context="N/A", candidate_profile="N/A", question_number=0, conversation_history="(warmup)")
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
app.include_router(company_router)
app.include_router(knowledge_router)
app.include_router(interview_agent)
app.include_router(avatar_ws_router)
app.include_router(templates_router)
app.include_router(analytics_router)
app.include_router(interview_ws_router)

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

class NgrokMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "true"
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

app.add_middleware(NgrokMiddleware)


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

