from app.models.llm import llm



def company_interviewer(state):


    prompt = f"""

You are an interviewer for this company.


Company Information:

{state["company_context"]}



Candidate Role:

{state["job_role"]}



Create ONE interview question.


Rules:

- Must relate to company industry
- Must match job role
- Do not ask unrelated questions
- Focus on real job responsibilities


"""


    response = llm.invoke(
        prompt
    )


    state["question"] = response.content.strip()



    return state