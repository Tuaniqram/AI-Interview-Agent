import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.database import get_supabase


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/companies",
    tags=["Companies"]
)


class CompanyCreate(BaseModel):

    name: str

    website: str | None = None

    description: str | None = None



@router.post("/")
def create_company(
    company: CompanyCreate
):

    try:

        db = get_supabase()


        result = db.table(
            "companies"
        ).insert({

            "name": company.name,

            "website": company.website,

            "description": company.description

        }).execute()


        return {
            "message": "Company created",
            "company": result.data[0]
        }


    except Exception as e:

        logger.error(
            f"Create company error: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



@router.get("/")
def get_companies():

    try:

        db = get_supabase()


        result = db.table(
            "companies"
        ).select("*").execute()


        return result.data


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



@router.get("/{company_id}")
def get_company(
    company_id:int
):

    try:

        db = get_supabase()


        result = db.table(
            "companies"
        ).select("*").eq(
            "id",
            company_id
        ).execute()


        if not result.data:

            raise HTTPException(
                status_code=404,
                detail="Company not found"
            )


        return result.data[0]


    except HTTPException:

        raise


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



@router.get("/{company_id}/sessions")
def get_company_sessions(company_id: int):
    """List all interview sessions for a company."""
    try:
        db = get_supabase()
        result = (
            db.table("interview_sessions")
            .select("id, candidate_id, job_role, status, final_score, started_at, created_at")
            .eq("company_id", company_id)
            .order("started_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error(f"Get company sessions error: {str(e)}")
        return []


@router.delete("/{company_id}")
def delete_company(
    company_id:int
):

    try:

        db = get_supabase()


        result = db.table(
            "companies"
        ).delete().eq(
            "id",
            company_id
        ).execute()


        return {
            "message":"Company deleted"
        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )