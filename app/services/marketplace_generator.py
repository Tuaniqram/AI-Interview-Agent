import logging

from sqlalchemy import select

from app.database.session import get_session_factory
from app.models.db import Department, Organization, PublicInterview
from app.services.llm_service import get_llm_service
from app.services.prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)


async def generate_rich_description(interview_id: str) -> None:
    """Background task: generate AI job description for a marketplace listing."""
    factory = get_session_factory()
    if factory is None:
        logger.error("No DB session factory — cannot generate rich description")
        return
    async with factory() as db:
        try:
            result = await db.execute(
                select(PublicInterview).where(PublicInterview.id == interview_id)
            )
            pi = result.scalar_one_or_none()
            if not pi:
                logger.warning(f"PublicInterview {interview_id} not found for rich_description generation")
                return

            org_result = await db.execute(
                select(Organization).where(Organization.id == pi.org_id)
            )
            org = org_result.scalar_one_or_none()
            org_name = org.name if org else "Our Company"

            dept_name = ""
            if pi.department_id:
                dept_result = await db.execute(
                    select(Department).where(Department.id == pi.department_id)
                )
                dept = dept_result.scalar_one_or_none()
                dept_name = dept.name if dept else ""

            loader = get_prompt_loader()
            prompt = loader.load_by_path(
                "marketplace/job_description.md",
                org_name=org_name,
                dept_name=dept_name,
                title=pi.title,
                interview_mode=pi.interview_mode,
                skills=pi.skills_required or "Not specified",
            )

            llm: LLMService = get_llm_service()
            result_text = await llm.invoke(
                prompt,
                temperature=0.7,
                max_tokens=600,
            )

            pi.rich_description = result_text.strip()
            await db.commit()
            logger.info(f"Rich description generated for interview {interview_id}")

        except Exception:
            logger.exception(f"Failed to generate rich description for interview {interview_id}")
