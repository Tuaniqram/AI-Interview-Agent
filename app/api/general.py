import os
import shutil
import logging
import shutil
import os

import logging

from app.models.llm import llm
from fastapi import APIRouter, HTTPException


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["general"]
)
@router.post("/ask")
def ask_company(data: dict):
    try:
        question = data.get("question", "")
        if not question:
            return {"error": "Question is required"}, 400

        from langchain_community.vectorstores import FAISS
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        db = FAISS.load_local(
            "vector_db",
            embeddings,
            allow_dangerous_deserialization=True
        )

        docs = db.similarity_search(question, k=3)

        context = "\n".join(doc.page_content for doc in docs)

        prompt = f"""
You are an HR interview assistant.

Use this company information:

{context}

Question:

{question}

Answer based only on company information.
"""

        response = llm.invoke(prompt)

        return {
            "question": question,
            "context": context,
            "answer": response.content
        }
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        return {"error": str(e)}, 500


from app.graph.workflow import graph


@router.post("/interview")
def interview(data: dict):
    try:
        if not data.get("job_role"):
            return {"error": "job_role is required"}, 400

        result = graph.invoke(data)
        logger.info("Interview workflow completed")
        return result

    except Exception as e:
        logger.error(f"Error in interview workflow: {str(e)}")
        return {"error": str(e)}, 500


@router.post("/interview/follow-up")
def interview_follow_up(data: dict):
    """Generate a follow-up question based on the candidate's previous answer"""
    try:
        if not data.get("job_role") or not data.get("previous_question") or not data.get("previous_answer"):
            return {"error": "job_role, previous_question, and previous_answer are required"}, 400

        job_role = data.get("job_role")
        previous_question = data.get("previous_question")
        previous_answer = data.get("previous_answer")
        company_context = data.get("company_context", "")

        prompt = f"""
You are a skilled technical interviewer conducting a follow-up in a real interview conversation.

Job Role: {job_role}

Company Context:
{company_context}

Previous Question You Asked:
{previous_question}

Candidate's Answer:
{previous_answer}

---

Based on what the candidate just said, generate ONE natural follow-up question that:
1. Digs deeper into what they mentioned
2. Explores their thinking, approach, or experience further
3. Sounds conversational - like you're continuing a natural conversation
4. Is 1-2 sentences, not a list
5. Shows genuine interest in their experience

Examples of GOOD follow-ups:
- "That's interesting - can you tell me more about how you handled that?"
- "I see, what was the biggest challenge you faced during that process?"
- "How did that experience shape the way you approach problems now?"

Just ask the follow-up question directly. No introduction or explanation needed.
"""

        response = llm.invoke(prompt)
        follow_up_question = response.content.strip()

        return {
            "job_role": job_role,
            "previous_question": previous_question,
            "previous_answer": previous_answer,
            "follow_up_question": follow_up_question
        }

    except Exception as e:
        logger.error(f"Error generating follow-up question: {str(e)}")
        return {"error": str(e)}, 500


@router.post("/interview/evaluate-with-followup")
def evaluate_with_followup(data: dict):
    """Evaluate answer and suggest follow-up question"""
    try:
        if not data.get("job_role") or not data.get("question") or not data.get("candidate_answer"):
            return {"error": "job_role, question, and candidate_answer are required"}, 400

        job_role = data.get("job_role")
        question = data.get("question")
        answer = data.get("candidate_answer")
        company_context = data.get("company_context", "")

        # Step 1: Evaluate the answer
        eval_prompt = f"""
You are an experienced technical interviewer evaluating a candidate's response.

Job Role: {job_role}

Company Requirements:
{company_context}

Question Asked:
{question}

Candidate's Answer:
{answer}

---

Provide feedback as a real interviewer would:

1. **Score**: 1-10
2. **Strengths**: What did they do well?
3. **Growth Areas**: What could be better?

Be honest, constructive, and conversational. Keep it brief.
"""

        eval_response = llm.invoke(eval_prompt)
        evaluation = eval_response.content.strip()

        # Step 2: Generate follow-up question
        followup_prompt = f"""
You are a technical interviewer. The candidate just answered this question:

Question: {question}
Their Answer: {answer}

Generate ONE natural follow-up question that digs deeper. Be conversational, not formal.
Just ask the question directly - no explanation needed.
"""

        followup_response = llm.invoke(followup_prompt)
        follow_up = followup_response.content.strip()

        return {
            "job_role": job_role,
            "question": question,
            "candidate_answer": answer,
            "evaluation": evaluation,
            "suggested_follow_up": follow_up
        }

    except Exception as e:
        logger.error(f"Error in evaluate_with_followup: {str(e)}")
        return {"error": str(e)}, 500
    