import logging

from fastapi import APIRouter, Body, HTTPException

from app.graph.company_workflow import company_graph
from app.models.llm import llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["company interview"]
)


@router.post("/companies/{company_id}/interview")
async def company_interview(
    company_id: int,
    data: dict = Body(...)
):
    try:
        if not data.get("job_role"):
            raise HTTPException(
                status_code=400,
                detail="job_role is required"
            )

        state = {
            "company_id": company_id,
            "job_role": data.get("job_role"),
            "candidate_answer": data.get("candidate_answer", ""),
            "question": "",
            "company_context": "",
            "feedback": ""
        }

        result = company_graph.invoke(state)

        logger.info(
            f"Interview started for company {company_id}"
        )

        return result

    except Exception as e:
        logger.exception("Interview error")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/companies/{company_id}/interview/follow-up")
async def company_interview_follow_up(
    company_id: int,
    data: dict = Body(...)
):
    try:

        required = [
            "job_role",
            "previous_question",
            "previous_answer"
        ]

        for field in required:
            if not data.get(field):
                raise HTTPException(
                    status_code=400,
                    detail=f"{field} is required"
                )

        prompt = f"""
You are a technical interviewer conducting a follow-up question.

Company ID:
{company_id}

Job Role:
{data.get("job_role")}

Previous Question:
{data.get("previous_question")}

Candidate Answer:
{data.get("previous_answer")}


Generate ONE natural follow-up question.

Rules:
- Dig deeper into the candidate's answer
- Ask about experience, approach, or reasoning
- Be conversational
- No explanation
"""

        response = llm.invoke(prompt)

        return {
            "company_id": company_id,
            "follow_up_question": response.content.strip()
        }


    except Exception as e:
        logger.exception("Follow-up generation failed")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/companies/{company_id}/interview/evaluate-with-followup")
async def company_evaluate_with_followup(
    company_id: int,
    data: dict = Body(...)
):
    try:

        required = [
            "job_role",
            "question",
            "candidate_answer"
        ]

        for field in required:
            if not data.get(field):
                raise HTTPException(
                    status_code=400,
                    detail=f"{field} is required"
                )


        evaluation_prompt = f"""
You are an experienced technical interviewer.

Company ID:
{company_id}

Job Role:
{data.get("job_role")}

Question:
{data.get("question")}

Candidate Answer:
{data.get("candidate_answer")}


Evaluate the answer.

Format:

**Score:** X / 10

**Strengths**
- ...

**Growth Areas**
- ...

Be honest and constructive.
"""


        evaluation_response = llm.invoke(
            evaluation_prompt
        )

        followup_prompt = f"""
You are a technical interviewer.

Question:
{data.get("question")}

Candidate Answer:
{data.get("candidate_answer")}


Generate ONE follow-up question.

Only output the question.
"""


        followup_response = llm.invoke(
            followup_prompt
        )


        return {
            "company_id": company_id,
            "job_role": data.get("job_role"),
            "question": data.get("question"),
            "candidate_answer": data.get("candidate_answer"),
            "evaluation": evaluation_response.content.strip(),
            "suggested_follow_up": followup_response.content.strip()
        }


    except Exception as e:
        logger.exception(
            "Evaluation with follow-up failed"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )