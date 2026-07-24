import logging
import os
import shutil
import uuid as libuuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_org_role, resolve_org_id
from app.database.deps import get_db
from app.models.db import Department, DepartmentDocument, InterviewSession, InterviewTemplate
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate

router = APIRouter(prefix="/departments", tags=["departments"])


UPLOAD_DIR = "documents"
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md"}


def _get_org_id(org_id: str = Depends(resolve_org_id)) -> str:
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Org-Id header is required")
    return org_id


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Department).where(Department.org_id == org_id).order_by(Department.name)
    )
    return [DepartmentResponse.model_validate(c) for c in result.scalars().all()]


@router.post("", response_model=DepartmentResponse)
async def create_department(
    req: DepartmentCreate,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    department = Department(org_id=org_id, **req.model_dump())
    db.add(department)
    await db.commit()
    await db.refresh(department)
    return DepartmentResponse.model_validate(department)


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Department).where(Department.id == department_id, Department.org_id == org_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return DepartmentResponse.model_validate(department)


@router.patch("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    req: DepartmentUpdate,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Department).where(Department.id == department_id, Department.org_id == org_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(department, field, value)
    await db.commit()
    await db.refresh(department)
    return DepartmentResponse.model_validate(department)


@router.delete("/{department_id}", status_code=204)
async def delete_department(
    department_id: int,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Department).where(Department.id == department_id, Department.org_id == org_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    await db.delete(department)
    await db.commit()


# ── Sessions ────────────────────────────────────────────────────────────


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
        select(Department).where(Department.id == department_id, Department.org_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    sess_result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.department_id == department_id)
        .order_by(InterviewSession.started_at.desc())
    )
    return [SessionSummaryResponse.model_validate(s) for s in sess_result.scalars().all()]


# ── Documents (knowledge) ──────────────────────────────────────────────


class DocumentResponse(BaseModel):
    id: UUID
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
        select(Department).where(Department.id == department_id, Department.org_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    doc_result = await db.execute(
        select(DepartmentDocument).where(DepartmentDocument.department_id == department_id).order_by(DepartmentDocument.created_at.desc())
    )
    return [DocumentResponse.model_validate(d) for d in doc_result.scalars().all()]


@router.post("/{department_id}/documents")
async def upload_document(
    department_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Department).where(Department.id == department_id, Department.org_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filepath = f"{UPLOAD_DIR}/{file.filename}"
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc_id = libuuid.uuid4()
    namespace = f"department_{department_id}"
    doc = DepartmentDocument(
        id=doc_id,
        department_id=department_id,
        filename=file.filename,
        document_type=ext.lstrip(".").lower() or "pdf",
        pinecone_namespace=namespace,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    if background_tasks:
        background_tasks.add_task(_process_document, filepath, department_id, str(doc_id), file.filename)

    return {
        "message": "Upload queued",
        "doc_id": str(doc_id),
        "filename": file.filename,
        "status": "processing",
    }


async def _process_document(filepath: str, department_id: int, doc_id: str, filename: str):
    try:
        from app.rag.loader import load_pdf
        from app.rag.splitter import split_documents
        from app.rag.pinecone_store import store_department_knowledge

        documents = load_pdf(filepath)
        chunks = split_documents(documents)
        store_department_knowledge(chunks, department_id, doc_id=doc_id)
        logging.getLogger(__name__).info(f"RAG pipeline completed: {len(chunks)} chunks stored (doc_id={doc_id})")
    except Exception as e:
        logging.getLogger(__name__).error(f"RAG pipeline failed for {filename} (doc_id={doc_id}): {e}")


@router.delete("/{department_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    department_id: int,
    doc_id: str,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Department).where(Department.id == department_id, Department.org_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    doc_result = await db.execute(
        select(DepartmentDocument).where(
            DepartmentDocument.id == doc_id,
            DepartmentDocument.department_id == department_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        from app.rag.pinecone_store import delete_department_knowledge
        delete_department_knowledge(department_id, doc_id)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Pinecone delete failed (continuing): {e}")

    filepath = os.path.join(UPLOAD_DIR, doc.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    await db.delete(doc)
    await db.commit()


# ── Templates ──────────────────────────────────────────────────────────


class TemplateCreateRequest(BaseModel):
    name: str
    job_role: str
    total_questions: int = 10


class TemplateResponse(BaseModel):
    id: str
    department_id: int
    name: str
    job_role: str
    total_questions: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/{department_id}/templates", response_model=list[TemplateResponse])
async def list_templates(
    department_id: int,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewTemplate)
        .join(Department, InterviewTemplate.department_id == Department.id)
        .where(Department.id == department_id, Department.org_id == org_id)
        .order_by(InterviewTemplate.created_at.desc())
    )
    return [TemplateResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/{department_id}/templates", response_model=TemplateResponse)
async def create_template(
    department_id: int,
    req: TemplateCreateRequest,
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    department_result = await db.execute(
        select(Department).where(Department.id == department_id, Department.org_id == org_id)
    )
    if not department_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    template = InterviewTemplate(
        id=libuuid.uuid4(),
        department_id=department_id,
        name=req.name,
        job_role=req.job_role,
        total_questions=req.total_questions,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return TemplateResponse.model_validate(template)
