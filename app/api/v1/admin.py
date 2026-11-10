import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import AdminOrgResponse, AdminUserResponse, PlatformStatsResponse
from app.admin.service import get_platform_stats, list_orgs, list_users, suspend_org
from app.auth.middleware import authenticate
from app.database.deps import get_db
from app.models.db import AuditLog, InterviewSession, Organization, User

router = APIRouter(prefix="/admin", tags=["admin"])

# Must match app/services/email.py: the templates that are actually sent.
EMAIL_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "emails" / "templates"


async def require_admin(user: User = Depends(authenticate)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


@router.get("/stats", response_model=PlatformStatsResponse)
async def stats_endpoint(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await get_platform_stats(db)


@router.get("/organizations", response_model=list[AdminOrgResponse])
async def list_orgs_endpoint(
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await list_orgs(search, db)


@router.post("/organizations/{org_id}/toggle-suspend")
async def toggle_suspend_endpoint(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    await suspend_org(org_id, db)
    return {"message": "Organization status toggled"}


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users_endpoint(
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await list_users(search, db)


# ── Audit log (all organizations) ──


@router.get("/audit-logs")
async def list_audit_logs(
    org_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = (
        select(AuditLog, Organization.name)
        .outerjoin(Organization, Organization.id == AuditLog.org_id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(limit)
    )
    if org_id:
        query = query.where(AuditLog.org_id == org_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    result = await db.execute(query)
    return [
        {
            "id": str(log.id),
            "org_id": str(log.org_id) if log.org_id else None,
            "org_name": org_name,
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log, org_name in result.all()
    ]


# ── LLM dashboard (platform-wide) ──


@router.get("/llm-status")
async def llm_status(admin: User = Depends(require_admin)):
    from app.api.v1.system import llm_provider_status
    from app.models.llm import _LLM_CONFIGS, llm

    return {
        "model_chain": llm.model_name,
        "providers": llm_provider_status(_LLM_CONFIGS),
    }


@router.get("/llm-usage")
async def llm_usage(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(
        select(
            func.count(InterviewSession.id).label("total_sessions"),
            func.sum(func.length(InterviewSession.final_feedback)).label("total_eval_chars"),
        )
    )
    row = result.one()
    return {
        "total_interviews": row.total_sessions,
        # About 36 model calls per 14-question interview (27-45 across the four test personas).
        "estimated_llm_calls": row.total_sessions * 36 if row.total_sessions else 0,
        "estimated_input_tokens": (row.total_eval_chars or 0) // 4,
    }


# ── Email template editor (global) ──


@router.get("/email-templates")
async def list_email_templates(admin: User = Depends(require_admin)):
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


@router.get("/email-templates/{name}")
async def get_email_template(
    name: str,
    admin: User = Depends(require_admin),
):
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise HTTPException(status_code=400, detail="Invalid template name")
    for ext in (".html", ".txt"):
        path = (EMAIL_TEMPLATES_DIR / f"{name}{ext}").resolve()
        if not str(path).startswith(str(EMAIL_TEMPLATES_DIR.resolve())):
            raise HTTPException(status_code=400, detail="Invalid template path")
        if path.exists():
            return {"name": name, "filename": path.name, "content": path.read_text(encoding="utf-8")}
    raise HTTPException(status_code=404, detail="Email template not found")


@router.put("/email-templates/{name}")
async def update_email_template(
    name: str,
    data: dict,
    admin: User = Depends(require_admin),
):
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise HTTPException(status_code=400, detail="Invalid template name — only letters, numbers, hyphens, and underscores allowed")
    content = data.get("content", "")
    ext = data.get("extension", ".html")
    if not re.match(r"^\.\w+$", ext):
        raise HTTPException(status_code=400, detail="Invalid file extension")
    EMAIL_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    path = (EMAIL_TEMPLATES_DIR / f"{name}{ext}").resolve()
    if not str(path).startswith(str(EMAIL_TEMPLATES_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid template path")
    path.write_text(content, encoding="utf-8")
    return {"message": "Template saved", "name": name, "filename": path.name}
