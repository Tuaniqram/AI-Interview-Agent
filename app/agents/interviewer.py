import logging
from app.models.llm import llm

logger = logging.getLogger(__name__)


def interview_agent(state):
    try:
        if not state.get('job_role') or not state.get('company_context'):
            logger.warning("Missing job_role or company_context in interview state")
            state["question"] = "Unable to generate question: missing context"
            return state

        prompt = f"""
You are an experienced technical interviewer conducting a real job interview.
Your style is conversational, professional, and genuinely curious about the candidate's experience.

You're interviewing for the role of: {state["job_role"]}

Company Context (what this role requires):
{state["company_context"]}

---

Your task: Generate ONE natural, conversational interview question that:
1. Relates directly to real-world challenges in this role
2. Invites the candidate to share practical experience
3. Sounds like something a real interviewer would ask (not scripted or formal)
4. Is open-ended and allows the candidate to showcase their thinking
5. Is about 1-3 sentences, not a list of sub-questions

Examples of GOOD conversational questions:
- "Tell me about a time you had to debug a complex performance issue. How did you approach it?"
- "What's the toughest technical challenge you've faced recently, and how did you overcome it?"
- "Can you walk me through a project where you had to make a tough architectural decision?"

Examples of BAD formal questions (DO NOT USE):
- "What are the five principles of...?"
- "List three ways to...?"
- "Define the following terms: ..."

Now generate ONE natural question for this specific role and company. Just ask the question directly - no introduction, no explanation. Make it sound like you're actually talking to the person.
"""

        response = llm.invoke(prompt)
        question_text = response.content.strip()
        
        # Store both the question and conversation context for follow-ups
        state["question"] = question_text
        state["interview_context"] = {
            "job_role": state["job_role"],
            "company_context": state["company_context"],
            "questions_asked": [question_text]
        }
        
        logger.info(f"Interview question generated for {state['job_role']}")
        return state

    except Exception as e:
        logger.error(f"Error in interview_agent: {str(e)}")
        state["question"] = f"Error generating question: {str(e)}"
        return state