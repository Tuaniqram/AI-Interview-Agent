import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_org_role_path
from app.config import settings
from app.database.deps import get_db
from app.models.db import InterviewSession, User

router = APIRouter(tags=["system"])


# ── Health ──


@router.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "app": "AI Interview Agent",
        "version": "2.0.0",
    }


# ── LLM Dashboard ──


@router.get("/api/v1/orgs/{org_id}/llm-status")
async def llm_status(
    _: User = Depends(require_org_role_path(["owner"])),
):
    from app.models.llm import llm

    return {
        "model_chain": llm.model_name,
        "providers": [
            {
                "name": "Groq (llama-3.3-70b)",
                "configured": bool(os.getenv("GROQ_API_KEY")),
            },
            {
                "name": "Local (one)",
                "configured": True,
            },
            {
                "name": "OpenRouter",
                "configured": bool(os.getenv("OPENROUTER_API_KEY")),
            },
        ],
    }


@router.get("/api/v1/orgs/{org_id}/llm-usage")
async def llm_usage(
    org_id: str,
    _: User = Depends(require_org_role_path(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            func.count(InterviewSession.id).label("total_sessions"),
            func.sum(func.length(InterviewSession.final_feedback)).label("total_eval_chars"),
        ).where(InterviewSession.org_id == org_id)
    )
    row = result.one()
    return {
        "total_interviews": row.total_sessions,
        "estimated_llm_calls": row.total_sessions * 20 if row.total_sessions else 0,
        "estimated_input_tokens": (row.total_eval_chars or 0) // 4,
    }


# ── Email Template Editor ──

EMAIL_TEMPLATES_DIR = Path("app/templates/email")


@router.get("/api/v1/orgs/{org_id}/email-templates")
async def list_email_templates(
    _: User = Depends(require_org_role_path(["owner"])),
):
    if not EMAIL_TEMPLATES_DIR.exists():
        return []
    templates = []
    for f in sorted(EMAIL_TEMPLATES_DIR.iterdir()):
        if f.suffix in (".html", ".txt"):
            templates.append({
                "name": f.stem,
                "filename": f.name,
                "path": str(f),
            })
    return templates


@router.get("/api/v1/orgs/{org_id}/email-templates/{name}")
async def get_email_template(
    name: str,
    _: User = Depends(require_org_role_path(["owner"])),
):
    for ext in (".html", ".txt"):
        path = EMAIL_TEMPLATES_DIR / f"{name}{ext}"
        if path.exists():
            return {"name": name, "filename": path.name, "content": path.read_text(encoding="utf-8")}
    raise HTTPException(status_code=404, detail="Email template not found")


@router.put("/api/v1/orgs/{org_id}/email-templates/{name}")
async def update_email_template(
    name: str,
    data: dict,
    _: User = Depends(require_org_role_path(["owner"])),
):
    content = data.get("content", "")
    ext = data.get("extension", ".html")
    EMAIL_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    path = EMAIL_TEMPLATES_DIR / f"{name}{ext}"
    path.write_text(content, encoding="utf-8")
    return {"message": "Template saved", "name": name, "filename": path.name}
