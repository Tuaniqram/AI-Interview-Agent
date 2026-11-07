import asyncio
import json
import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db import CandidateDocument
from app.models.llm import llm

logger = logging.getLogger(__name__)

RESUMES_DIR = Path("resumes")

ALLOWED_EXTENSIONS = {".pdf"}
MAX_RESUME_BYTES = 5 * 1024 * 1024
MAX_EXTRACTED_CHARS = 20000


async def _ensure_dir():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: RESUMES_DIR.mkdir(parents=True, exist_ok=True))


async def save_resume_file(candidate_id: uuid.UUID, file) -> str:
    await _ensure_dir()
    ext = ".pdf"
    filename = f"{candidate_id}{ext}"
    filepath = RESUMES_DIR / filename

    def _write():
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _write)
    return str(filepath)


async def extract_text_from_bytes(content: bytes) -> str:
    def _read():
        import io

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    text = await asyncio.get_running_loop().run_in_executor(None, _read)
    return text.strip()


async def extract_text(filepath: str) -> str:
    def _read():
        reader = PdfReader(filepath)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, _read)
    return text.strip()


async def parse_resume(text: str) -> dict:
    prompt = f"""Extract structured information from this resume text. Return ONLY valid JSON with no markdown formatting or code blocks.

Extract:
- skills: array of strings (technical skills, tools, technologies, languages)
- experience: array of {{ company, role, duration, description }}
- education: array of {{ institution, degree, year }}
- headline: a one-line professional summary
- years_of_experience: number (estimate if not explicit)

Resume text:
{text[:8000]}"""

    try:
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        data = json.loads(content)
    except Exception as e:
        logger.warning("LLM resume parsing failed: %s", e)
        data = {"skills": [], "experience": [], "education": [], "headline": "", "years_of_experience": None}
    return data


async def store_candidate_resume(candidate, file, db: AsyncSession) -> CandidateDocument:
    """Validate, save and register a candidate's PDF CV; returns the new document.

    Shared by the authenticated profile upload and the apply flow (guest or
    logged-in). Validates the PDF, extracts its text, stores the file through
    ``app.services.cv_storage`` (local disk or Supabase Storage), creates a
    ``candidate_documents`` row, and points ``candidate.resume_url`` at the stored
    file. The caller owns the commit.
    """
    filename = (getattr(file, "filename", None) or "resume.pdf")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CV file is empty")
    if len(content) > MAX_RESUME_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CV file is too large (max 5 MB)")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CV is not a valid PDF file")

    document_id = uuid.uuid4()

    # Read the text before storing anything: a PDF we cannot parse is rejected and never stored.
    try:
        text = await extract_text_from_bytes(content)
    except Exception as exc:
        logger.warning("Could not read uploaded PDF %s: %s", filename, exc)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not read the PDF; upload a text-based PDF")

    from app.services import cv_storage

    try:
        ref = await cv_storage.save(f"{candidate.id}/{document_id.hex}.pdf", content)
    except cv_storage.CVStorageError as exc:
        logger.error("CV storage failed: %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Could not store the CV right now. Please try again.")

    document = CandidateDocument(
        id=document_id,
        candidate_id=candidate.id,
        filename=filename,
        document_type="resume",
        extracted_text=(text or "")[:MAX_EXTRACTED_CHARS],
        document_metadata={"ext": "pdf", "path": ref, "size": len(content)},
    )
    db.add(document)
    candidate.resume_url = ref
    await db.flush()
    return document


async def latest_resume_document(candidate_id: uuid.UUID, db: AsyncSession) -> CandidateDocument | None:
    """Most recent resume document for a candidate, if any."""
    result = await db.execute(
        select(CandidateDocument)
        .where(
            CandidateDocument.candidate_id == candidate_id,
            CandidateDocument.document_type == "resume",
        )
        .order_by(CandidateDocument.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
