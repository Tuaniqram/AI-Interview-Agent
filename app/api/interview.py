import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Depends, Path
from pydantic import BaseModel

from app.models.llm import llm
from app.config.database import get_supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["company interview"]
)

# ============================================================================
# DATABASE CLIENT
# ============================================================================

supabase = get_supabase()
# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SessionStartRequest(BaseModel):
    job_role: str

class AnswerRequest(BaseModel):
    job_role: str
    session_id: str
    question: str
    candidate_answer: str
    conversation_history: Optional[str] = ""
    current_phase: Optional[str] = None
    difficulty_level: Optional[int] = None
    question_number: Optional[int] = None

# ============================================================================
# DEPRECATED ENDPOINTS (KEPT FOR BACKWARD COMPATIBILITY)
# ============================================================================


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


# ============================================================================
# NEW PHASE-AWARE INTERVIEW ENDPOINTS
# ============================================================================

PHASE_TEMPLATES = {
    "intro": {
        "count": 2,
        "focus": "Build rapport, understand candidate background",
        "example_questions": [
            "Tell me about yourself and your career background.",
            "What interests you about this role and our company?"
        ]
    },
    "experience": {
        "count": 3,
        "focus": "Deep dive into candidate history, validate resume claims",
        "example_questions": [
            "Can you walk me through your most complex project?",
            "What were your key responsibilities in that role?",
            "What technologies did you use and why?"
        ]
    },
    "technical": {
        "count": 5,
        "focus": "Evaluate core technical abilities",
        "difficulty_checkpoints": {
            "max_questions": 10,
            "easy_bonus": 2,
            "medium_bonus": 1
        },
        "example_questions": [
            "How would you design a scalable API for our use case?",
            "Tell me about a performance bottleneck you faced and how you solved it.",
            "How do you handle data validation and security considerations?",
            "Can you explain your approach to database optimization?",
            "Walk me through your CI/CD pipeline."
        ]
    },
    "behavioral": {
        "count": 3,
        "focus": "Evaluate soft skills using STAR method",
        "example_questions": [
            "Tell me about a time you failed and what you learned.",
            "Describe a conflict with a teammate and how you resolved it.",
            "How do you handle tight deadlines and pressure?"
        ]
    },
    "conclusion": {
        "count": 999,
        "focus": "Wrap up interview, candidate questions, next steps",
        "example_questions": [
            "Do you have any questions for us?",
            "Is there anything else you would like to add about your qualifications?",
            "What are you looking for in your next role?"
        ]
    }
}

def get_phase_from_databse(session_id: str) -> dict:
    """Retrieve session state from database"""
    try:
        response = supabase.table("interview_sessions").select("*").eq("id", session_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return response.data[0]
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/companies/{company_id}/interview/session")
async def start_interview_session(
    company_id: int,
    request: SessionStartRequest,
    current_phase: str = "intro"
):
    """
    Create a new interview session
    
    Body: { "job_role": str }
    
    Returns: {
        "session_id": str,
        "current_phase": str,
        "question_number": int,
        "total_questions": int
    }
    """
    try:
        if not request.job_role:
            raise HTTPException(
                status_code=400,
                detail="job_role is required"
            )

        # Generate UUID
        session_id = str(uuid.uuid4())
        
        # Calculate total questions across ALL phases (intro + experience
        # + technical + behavioral + conclusion) so the interview does not
        # end prematurely after the first phase.
        phase_config = PHASE_TEMPLATES.get(current_phase, PHASE_TEMPLATES["intro"])
        total_questions = (
            PHASE_TEMPLATES["intro"]["count"]
            + PHASE_TEMPLATES["experience"]["count"]
            + PHASE_TEMPLATES["technical"]["count"]
            + PHASE_TEMPLATES["behavioral"]["count"]
            + 2  # conclusion wrap-up
        )
        
        # Insert into database
        response = supabase.table("interview_sessions").insert({
            "id": session_id,
            "company_id": company_id,
            "job_role": request.job_role,
            "status": "active",
            "current_phase": current_phase,
            "current_question_number": 0,
            "total_questions": total_questions,
            "started_at": "now()",
            "final_feedback": None
        }).execute()
        
        logger.info(f"Created new session {session_id} for company {company_id} in phase {current_phase}")
        
        return {
            "session_id": session_id,
            "current_phase": current_phase,
            "question_number": 0,
            "total_questions": total_questions
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Session creation failed")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/companies/{company_id}/interview/session/{session_id}")
async def get_session_status(
    company_id: int,
    session_id: str
):
    """Retrieve current session state"""
    try:
        session = get_phase_from_databse(session_id)
        
        # Check if we have any messages
        messages_response = supabase.table("interview_messages").select("*").eq("session_id", session_id).execute()
        
        return {
            "session_id": session_id,
            "company_id": session["company_id"],
            "job_role": session["job_role"],
            "status": session["status"],
            "current_phase": session["current_phase"],
            "question_number": session["current_question_number"],
            "total_questions": session["total_questions"],
            "final_score": session["final_score"],
            "interview_complete": len(messages_response.data) >= session["question_number"] if session["question_number"] else False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to retrieve session")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/companies/{company_id}/interview/session/{session_id}/next")
async def get_next_question(
    company_id: int,
    session_id: str,
    data: dict = Body(...)
):
    """
    Get next question based on phase, history, and performance
    
    Body: {
        "job_role": str,
        "conversation_history": str,  // Optional
        "current_phase": str,  // Override from DB if ambiguous
        "question_number": int,  // Override from DB
        "difficulty_level": int,  // Override from DB if tracking
        "previous_scores": list  // Optional list of scores
    }
    
    Returns: {
        "question": str,
        "phase": str,
        "question_number": int,
        "difficulty_level": int,
        "interview_status": str
    }
    """
    try:
        # Get database state
        session = get_phase_from_databse(session_id)
        
        current_phase = data.get("current_phase") or session["current_phase"]
        question_number = int(
            data.get("question_number")
            if data.get("question_number") is not None
            else session["current_question_number"]
        )
        difficulty_level = int(data.get("difficulty_level", 1))
        previous_scores = data.get("previous_scores", [])
        
        # Get conversation history
        history_response = supabase.table("interview_messages").select("*").eq("session_id", session_id).order("created_at").execute()
        
        conversation_history = ""
        if history_response.data:
            conversation_history = "\n\n".join([
                f"Q: {msg.get('message_type', '')}\nA: {msg.get('content', '')}"
                for msg in history_response.data
            ])
        
        # Get phase configuration
        phase_config = PHASE_TEMPLATES.get(current_phase, PHASE_TEMPLATES["intro"])
        
        # Calculate question to ask
        # If we're in technical phase, check scoring history for difficulty
        if current_phase == "technical" and previous_scores:
            avg_score = sum(previous_scores) / len(previous_scores) if previous_scores else 0
            
            if avg_score > 7:  # Strong candidate
                if question_number < 5:
                    difficulty = 3  # Increase difficulty
                else:
                    # Skip to conclusion
                    logger.info(f"Strong candidate, skipping to conclusion")
                    return await _fade_to_conclusion(company_id, session_id, question_number)
            elif avg_score < 5:  # Weak candidate
                difficulty = 1  # Easier questions
            else:  # Average - moderate difficulty
                difficulty = 2
        
        # If we've reached conclusion phase (forced or natural)
        if current_phase == "conclusion":
            logger.info(f"Interview in conclusion phase at question {question_number}")
            return await _fade_to_conclusion(company_id, session_id, question_number)
        
        # Determine which question to ask
        if question_number < len(phase_config["example_questions"]):
            question_text = phase_config["example_questions"][question_number]
        else:
            # Generate AI question based on phase and history
            question_text = await _generate_phase_appropriate_question(
                company_id=company_id,
                job_role=session["job_role"],
                phase=current_phase,
                difficulty_level=difficulty_level,
                conversation_history=conversation_history
            )
        
        # Update question number in session
        response = supabase.table("interview_sessions").update({
            "current_question_number": question_number + 1
        }).eq("id", session_id).execute()
        
        logger.info(f"Generated question {question_number + 1} in phase {current_phase}")
        
        return {
            "question": question_text,
            "phase": current_phase,
            "question_number": question_number + 1,
            "difficulty_level": difficulty_level,
            "interview_status": "in_progress"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get next question")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/companies/{company_id}/interview/answer")
async def submit_candidate_answer(
    company_id: int,
    data: AnswerRequest
):
    """
    Submit candidate answer, get evaluation, and generate adaptive follow-up
    
    Body: {
        "job_role": str,
        "session_id": str,
        "question": str,
        "candidate_answer": str,
        "conversation_history": str,  // Optional
        "current_phase": str,
        "difficulty_level": int,
        "question_number": int
    }
    
    Returns: {
        "evaluation": str,  // Full feedback
        "suggested_follow_up": str,  // Adaptive question
        "phase": str,  // May change if we skip phases
        "question_number": int,  // Incremented
        "difficulty_level": int,  // May change based on performance
        "interview_status": str  // "completed" or "in_progress"
    }
    """
    try:
        # Get phase from database
        session = get_phase_from_databse(data.session_id)
        current_phase = data.current_phase or session["current_phase"]
        question_number = int(
            data.question_number
            if data.question_number is not None
            else session["current_question_number"]
        )
        
        difficulty_level = int(data.difficulty_level or 1)
        final_score = session.get("final_score")
        previous_scores = final_score / 10 if final_score else 0
        
        # Evaluate the answer
        evaluation_result = await _evaluate_answer(
            job_role=data.job_role,
            company_id=company_id,
            question=data.question,
            candidate_answer=data.candidate_answer,
            current_phase=current_phase,
            difficulty_level=difficulty_level
        )
        
        # Determine adaptive features
        score = evaluation_result.get("score", 7)
        next_phase, next_difficulty, next_status = await _adapt_to_performance(
            current_phase=current_phase,
            question_number=question_number,
            score=score,
            session_id=data.session_id
        )
        
        # Insert evaluation into DB
        message_entry = supabase.table("interview_messages").insert({
            "session_id": data.session_id,
            "role": "candidate",
            "message_type": data.question,
            "content": data.candidate_answer,
            "question_number": question_number + 1,
            "phase": current_phase,
            "score": score,
            "evaluated_at": "now()"
        }).execute()
        
        # Insert evaluation details
        supabase.table("interview_evaluations").insert({
            "session_id": data.session_id,
            "message_id": message_entry.data[0]["id"],
            "score": score,
            "technical_score": evaluation_result.get("technical_score", score),
            "communication_score": evaluation_result.get("communication_score", score),
            "strengths": evaluation_result.get("strengths", ""),
            "weaknesses": evaluation_result.get("weaknesses", ""),
            "feedback_detail": evaluation_result.get("evaluation", ""),
            "evaluated_at": "now()"
        }).execute()
        
        # Calculate final score if this is last question
        question_number = int(question_number)
        total_questions = int(session["total_questions"])

        new_question_number = question_number + 1
        # Interview completes only when the phase machine says so (e.g.
        # conclusion -> completed) OR we've genuinely exhausted the grand
        # total question budget across all phases. This prevents the
        # interview from ending right after the intro phase.
        should_complete = (next_status == "completed") or (new_question_number >= total_questions)

        if should_complete:
            final_score = next_difficulty * 2 + (score - 5) * 0.5  # Approximate calculation
            final_score = min(10, max(0, final_score))
            
            supabase.table("interview_sessions").update({
                "current_question_number": new_question_number,
                "current_phase": next_phase,
                "final_score": final_score,
                "final_feedback": evaluation_result.get("evaluation", ""),
                "status": "completed",
                "ended_at": "now()"
            }).eq("id", data.session_id).execute()
            
            next_status = "completed"
        else:
            # Update session for next iteration (persist phase so the
            # frontend/DB stay in sync across turns)
            supabase.table("interview_sessions").update({
                "current_question_number": new_question_number,
                "current_phase": next_phase
            }).eq("id", data.session_id).execute()
        
        return {
            "evaluation": evaluation_result.get("evaluation", ""),
            "suggested_follow_up": evaluation_result.get("suggested_follow_up", ""),
            "phase": next_phase,
            "question_number": new_question_number,
            "difficulty_level": next_difficulty,
            "interview_status": next_status,
            "score": score
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to evaluate answer")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

async def _evaluate_answer(
    job_role: str,
    company_id: int,
    question: str,
    candidate_answer: str,
    current_phase: str,
    difficulty_level: int
) -> dict:
    """Call evaluator agent with appropriate context"""
    
    # Build contextual prompt
    evaluator_prompt = f"""
You are an experienced technical interviewer evaluating a candidate's response.

Job Role: {job_role}

Company Requirements: (Company {company_id} context would go here)

Question Asked:
{question}

Candidate's Answer:
{candidate_answer}

Phase: {current_phase}
Difficulty Level: {difficulty_level}

Your task: Provide detailed feedback to help the candidate improve.

Format your evaluation in the following structure:

**Score:** X / 10

**Breakdown:**
- Technical Knowledge: X / 10
- Problem Solving: X / 10
- Communication: X / 10
- Overall Impression: X / 10

**Strengths:**
- ...

**Areas for Growth:**
- ...

**Suggested Follow-up Question:**
Next, ask ONE question that digs deeper into the area you identified for growth. Use the STAR method if appropriate.

**Overall Feedback:**
Write one sentence summarizing how you would rate this candidate for this role.
"""
    
    try:
        response = llm.invoke(evaluator_prompt)
        feedback_text = response.content.strip()
        
        # Parse scores (basic extraction)
        score_match = feedback_text.split("\n")  # Multiple extracts
        
        score = 7  # Default if not found
        strengths = []
        weaknesses = []
        suggested_follow_up = ""
        found=False
        for line in score_match:
            if line.strip().startswith("**Score:"):
                # Extract numeric score
                for word in line.split():
                    try:
                        score = float(word.replace("/", "").replace(":", "").strip())
                        break
                    except:
                        pass
            elif line.strip().startswith("**Strengths"):
                # Next lines are strengths
                for following_line in score_match:
                    line = following_line.strip()
                    if line and not line.startswith("**"):
                        strengths.append(line)
                    elif line.startswith("**"):
                        break
            elif line.strip().startswith("**Areas for Growth"):
                # Next lines are weaknesses
                for following_line in score_match:
                    line = following_line.strip()
                    if line and not line.startswith("**"):
                        weaknesses.append(line)
                    elif line.startswith("**"):
                        break
            elif "Suggested Follow-up" in line:
                found = True
                continue

            elif found and line.strip():
                suggested_follow_up = (
                    line
                    .replace(">", "")
                    .replace('"', "")
                    .strip()
                )
        
        return {
            "evaluation": feedback_text,
            "score": score,
            "strengths": ", ".join(strengths[-5:]) if strengths else "None identified",
            "weaknesses": ", ".join(weaknesses[-5:]) if weaknesses else "None identified",
            "technical_score": score - 1 if current_phase == "technical" else score,
            "communication_score": score - 0.5,
            "suggested_follow_up": suggested_follow_up if suggested_follow_up else ""
        }
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {
            "evaluation": "There was an error evaluating your answer. Please try again.",
            "score": 5,
            "strengths": "N/A",
            "weaknesses": "N/A",
            "suggested_follow_up": ""
        }

async def _generate_phase_appropriate_question(
    company_id: int,
    job_role: str,
    phase: str,
    difficulty_level: int,
    conversation_history: str
) -> str:
    """Generate phase-appropriate question using LLM"""
    
    phase_context = PHASE_TEMPLATES[phase]["focus"]
    
    prompt = f"""
You are an experienced technical interviewing for the {job_role} role.
Company ID: {company_id}

PHASE CONTEXT: {phase_context}
DIFFICULTY LEVEL: {difficulty_level}

PREVIOUS CONVERSATION:
{conversation_history}

Your task: Generate ONE natural, professional interview question for this candidate.

Rules:
1. Match the phase: {phase_context}
2. Base difficulty: {difficulty_level} (1=easy, 2=medium, 3=hard)
3. Be conversational - natural, not robotic
4. Invite details, don't quiz
5. About 1-3 sentences
6. Build on previous conversation if applicable

Example for Intro phase:
"Tell me about your background and what brings you to this field."

Example for Technical phase (difficulty 3):
"How would you approach designing a system that needs to handle 10,000 concurrent users?"

Generate ONE question now:
"""

    try:
        response = llm.invoke(prompt)
        question = response.content.strip()
        return question
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        return "Can you tell me more about your experience in this area?"

async def _adapt_to_performance(
    current_phase: str,
    question_number: int,
    score: float,
    session_id: str
) -> tuple:
    """Adapt phase, difficulty, and status based on performance"""
    
    next_phase = current_phase
    next_difficulty = 1  # Default to easy
    next_status = "in_progress"
    
    # Adapt difficulty based on score
    if score > 7.0:
        next_difficulty = 3  # Hard
    elif score > 5.0:
        next_difficulty = 2  # Medium
    else:
        next_difficulty = 1  # Easy
    
    # Phase transitions
    if current_phase == "intro" and question_number >= 2:
        next_phase = "experience"
    
    elif current_phase == "experience" and question_number >= 5:
        next_phase = "technical"
    
    elif current_phase == "technical":
        # Technical phase special logic
        if score < 5.0:
            # Weak performance - stay in technical phase
            next_phase = "technical"
        elif score > 7.0 and question_number >= 8:
            # Strong performance - fade to conclusion
            next_status = await _fade_to_conclusion_logic(question_number)
            next_phase = "conclusion"
        # else: stay in technical phase
    
    elif current_phase == "behavioral" and question_number >= 3:
        next_phase = "conclusion"
    
    elif current_phase == "conclusion":
        next_status = "completed"
    
    return next_phase, next_difficulty, next_status

async def _fade_to_conclusion(company_id: int, session_id: str, question_number: int) -> dict:
    """Force transition to conclusion phase"""
    
    # Update session
    supabase.table("interview_sessions").update({
        "current_phase": "conclusion",
        "current_question_number": question_number
    }).eq("id", session_id).execute()
    
    return {
        "question": "Before we continue, do you have any questions about the role or our company?",
        "phase": "conclusion",
        "question_number": question_number,
        "difficulty_level": 1,
        "interview_status": "in_progress"
    }

async def _fade_to_conclusion_logic(question_number):
    """Internal helper for conclusion logic"""
    return "completed"