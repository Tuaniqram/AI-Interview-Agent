import asyncio
import logging
import os
import re
import shutil
import uuid as libuuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_org_role, resolve_org_id
from app.database.deps import get_db
from app.models.db import InterviewSession, InterviewTemplate, Organization, OrganizationDocument
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services.it_role_resolver import resolve_it_role

router = APIRouter(prefix="/departments", tags=["departments"])

UPLOAD_DIR = "documents"
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md"}
logger = logging.getLogger(__name__)


def _get_org_id(org_id: str = Depends(resolve_org_id)) -> str:
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Org-Id header is required")
    return org_id


async def _org_or_404(org_id: str, db: AsyncSession) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


def _synthetic_department(org: Organization) -> DepartmentResponse:
    return DepartmentResponse(
        id=0,
        org_id=org.id,
        name="IT Department",
        website=org.website,
        description=org.description,
        created_at=org.created_at,
    )


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    org = await _org_or_404(org_id, db)
    return [_synthetic_department(org)]


@router.post("", response_model=DepartmentResponse)
async def create_department(
    req: DepartmentCreate,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Departments are not configurable; IT documents belong to the organization",
    )


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    org = await _org_or_404(org_id, db)
    return _synthetic_department(org)


@router.patch("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    req: DepartmentUpdate,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    org = await _org_or_404(org_id, db)
    data = req.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        org.name = data["name"]
    if "website" in data:
        org.website = data["website"]
    if "description" in data:
        org.description = data["description"]
    await db.commit()
    await db.refresh(org)
    return _synthetic_department(org)


@router.delete("/{department_id}", status_code=204)
async def delete_department(
    department_id: int,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Departments are not configurable; delete organization documents instead",
    )


class SessionSummaryResponse(BaseModel):
    id: str
    job_role: str
    status: Optional[str] = None
    final_score: Optional[float] = None
    started_at: Optional[datetime] = None
    interaction_mode: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("/{department_id}/sessions", response_model=list[SessionSummaryResponse])
async def list_department_sessions(
    department_id: int,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.org_id == org_id)
        .order_by(InterviewSession.started_at.desc())
        .limit(100)
    )
    return [
        SessionSummaryResponse(
            id=str(s.id),
            job_role=s.job_role_snapshot,
            status=s.status,
            final_score=float(s.final_score) if s.final_score is not None else None,
            started_at=s.started_at,
            interaction_mode=s.interaction_mode,
        )
        for s in result.scalars().all()
    ]


class DocumentResponse(BaseModel):
    id: str
    filename: str
    document_type: str
    pinecone_namespace: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/{department_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    department_id: int,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationDocument)
        .where(OrganizationDocument.org_id == org_id)
        .order_by(OrganizationDocument.created_at.desc())
    )
    return [
        DocumentResponse(
            id=str(d.id),
            filename=d.filename,
            document_type=d.document_type,
            pinecone_namespace=d.pinecone_namespace,
            created_at=d.created_at,
        )
        for d in result.scalars().all()
    ]


@router.post("/{department_id}/documents")
async def upload_document(
    department_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    await _org_or_404(org_id, db)

    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    def _save():
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", file.filename or "document.pdf")
        filepath = os.path.join(UPLOAD_DIR, safe_filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return filepath

    loop = asyncio.get_running_loop()
    filepath = await loop.run_in_executor(None, _save)

    doc_id = libuuid.uuid4()
    namespace = f"department_{org_id}"
    doc = OrganizationDocument(
        id=doc_id,
        org_id=org_id,
        filename=file.filename,
        document_type=ext.lstrip(".").lower() or "pdf",
        pinecone_namespace=namespace,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    if background_tasks:
        background_tasks.add_task(_process_document, filepath, org_id, str(doc_id), file.filename)

    return {
        "message": "Upload queued",
        "doc_id": str(doc_id),
        "filename": file.filename,
        "status": "processing",
    }


def _invalidate_org_brain(org_id) -> None:
    """Drop cached company brains so new/removed documents are used next session."""
    try:
        from app.intelligence.company_cache import invalidate_company_brain

        invalidate_company_brain(org_id=str(org_id))
    except Exception as exc:  # noqa: BLE001 - cache eviction is best-effort
        logger.warning(f"Company brain cache invalidation failed: {exc}")


async def _process_document(filepath: str, org_id: str, doc_id: str, filename: str):
    try:
        from app.rag.loader import load_pdf
        from app.rag.splitter import split_documents
        from app.rag.pinecone_store import store_department_knowledge

        documents = load_pdf(filepath)
        chunks = split_documents(documents)
        store_department_knowledge(chunks, org_id, doc_id=doc_id)
        _invalidate_org_brain(org_id)
        logger.info(f"RAG pipeline completed: {len(chunks)} chunks stored (doc_id={doc_id})")
    except Exception as e:
        logger.error(f"RAG pipeline failed for {filename} (doc_id={doc_id}): {e}")


@router.delete("/{department_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    department_id: int,
    doc_id: str,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    doc_result = await db.execute(
        select(OrganizationDocument).where(
            OrganizationDocument.id == doc_id,
            OrganizationDocument.org_id == org_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        from app.rag.pinecone_store import delete_department_knowledge
        delete_department_knowledge(org_id, doc_id)
    except Exception as e:
        logger.warning(f"Pinecone delete failed (continuing): {e}")
    _invalidate_org_brain(org_id)

    filepath = os.path.join(UPLOAD_DIR, doc.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    await db.delete(doc)
    await db.commit()


class TemplateCreateRequest(BaseModel):
    name: str
    job_role: str
    level_code: Optional[str] = None
    description: Optional[str] = None
    interview_style: Optional[str] = "STANDARD"
    competencies: Optional[list[dict]] = None
    total_questions: int = 10
    scorecard_template_id: Optional[str] = None


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    job_role: Optional[str] = None
    level_code: Optional[str] = None
    description: Optional[str] = None
    interview_style: Optional[str] = None
    competencies: Optional[list[dict]] = None
    total_questions: Optional[int] = None
    scorecard_template_id: Optional[str] = None


class TemplateResponse(BaseModel):
    id: UUID
    department_id: int = 0
    it_role_id: Optional[UUID] = None
    name: str
    job_role: str
    level_code: Optional[str] = None
    description: Optional[str] = None
    interview_style: Optional[str] = None
    competencies: Optional[list] = None
    total_questions: Optional[int] = None
    scorecard_template_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


def _template_response(t: InterviewTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=t.id,
        department_id=0,
        it_role_id=t.it_role_id,
        name=t.name,
        job_role=t.job_role_snapshot,
        level_code=t.level_code,
        description=t.description,
        interview_style=t.interview_style,
        competencies=t.competencies,
        total_questions=t.total_questions,
        scorecard_template_id=t.scorecard_template_id,
        created_at=t.created_at,
    )


@router.get("/{department_id}/templates", response_model=list[TemplateResponse])
async def list_templates(
    department_id: int,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewTemplate)
        .where(InterviewTemplate.org_id == org_id)
        .order_by(InterviewTemplate.created_at.desc())
    )
    return [_template_response(t) for t in result.scalars().all()]


@router.post("/{department_id}/templates", response_model=TemplateResponse)
async def create_template(
    department_id: int,
    req: TemplateCreateRequest,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    await _org_or_404(org_id, db)
    it_role = await resolve_it_role(db, req.job_role)

    template = InterviewTemplate(
        id=libuuid.uuid4(),
        org_id=org_id,
        it_role_id=it_role.id,
        level_code=req.level_code,
        name=req.name,
        job_role_snapshot=req.job_role,
        description=req.description,
        interview_style=req.interview_style,
        competencies=req.competencies,
        total_questions=req.total_questions,
        scorecard_template_id=UUID(req.scorecard_template_id) if req.scorecard_template_id else None,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return _template_response(template)


@router.get("/{department_id}/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    department_id: int,
    template_id: str,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewTemplate).where(
            InterviewTemplate.id == template_id,
            InterviewTemplate.org_id == org_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return _template_response(template)


@router.put("/{department_id}/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    department_id: int,
    template_id: str,
    req: TemplateUpdateRequest,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewTemplate).where(
            InterviewTemplate.id == template_id,
            InterviewTemplate.org_id == org_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    update_data = req.model_dump(exclude_unset=True)
    if "job_role" in update_data:
        it_role = await resolve_it_role(db, update_data.pop("job_role"))
        template.it_role_id = it_role.id
        template.job_role_snapshot = it_role.name
    if "scorecard_template_id" in update_data:
        value = update_data["scorecard_template_id"]
        update_data["scorecard_template_id"] = UUID(value) if value else None
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return _template_response(template)


@router.delete("/{department_id}/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    department_id: int,
    template_id: str,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewTemplate).where(
            InterviewTemplate.id == template_id,
            InterviewTemplate.org_id == org_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    await db.delete(template)
    await db.commit()
