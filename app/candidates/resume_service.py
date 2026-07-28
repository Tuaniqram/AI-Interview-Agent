import asyncio
import json
import logging
import os
import shutil
import uuid
from pathlib import Path

from pypdf import PdfReader

from app.config import settings
from app.models.llm import llm

logger = logging.getLogger(__name__)

RESUMES_DIR = Path("resumes")

ALLOWED_EXTENSIONS = {".pdf"}


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
