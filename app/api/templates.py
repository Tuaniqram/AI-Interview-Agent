"""
Interview Templates API - CRUD for reusable interview configurations.
"""
import logging
from pydantic import BaseModel
from typing import Optional
from fastapi import APIRouter, HTTPException

from app.config.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/templates",
    tags=["Templates"]
)


class TemplateCreate(BaseModel):
    company_id: int
    name: str
    job_role: str
    total_questions: int = 10
    interview_type: str = "typing"
    candidate_name: str = ""
    candidate_email: str = ""


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    job_role: Optional[str] = None
    total_questions: Optional[int] = None
    interview_type: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None


@router.get("/")
def list_templates(company_id: Optional[int] = None):
    """List all templates, optionally filtered by company."""
    try:
        db = get_supabase()
        query = db.table("interview_templates").select("*")
        if company_id is not None:
            query = query.eq("company_id", company_id)
        result = query.order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        logger.error(f"List templates error: {e}")
        return []


@router.post("/")
def create_template(template: TemplateCreate):
    """Create a new interview template."""
    try:
        db = get_supabase()
        result = db.table("interview_templates").insert({
            "company_id": template.company_id,
            "name": template.name,
            "job_role": template.job_role,
            "total_questions": template.total_questions,
            "interview_type": template.interview_type,
            "candidate_name": template.candidate_name,
            "candidate_email": template.candidate_email,
        }).execute()
        return result.data[0]
    except Exception as e:
        logger.error(f"Create template error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}")
def update_template(template_id: str, updates: TemplateUpdate):
    """Update an existing template."""
    try:
        db = get_supabase()
        data = {k: v for k, v in updates.model_dump().items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")
        result = db.table("interview_templates").update(data).eq("id", template_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Template not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update template error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
def delete_template(template_id: str):
    """Delete a template."""
    try:
        db = get_supabase()
        db.table("interview_templates").delete().eq("id", template_id).execute()
        return {"message": "Template deleted"}
    except Exception as e:
        logger.error(f"Delete template error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
