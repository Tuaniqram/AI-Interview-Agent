from app.models.llm import llm



def company_evaluator(state):


    prompt = f"""

You are evaluating a candidate.


Company:

{state["company_context"]}



Role:

{state["job_role"]}



Question:

{state["question"]}



Answer:

{state["candidate_answer"]}



Give feedback:


**Score:** X / 10


**Strengths**

-


**Growth Areas**

-


"""


    response = llm.invoke(
        prompt
    )



    state["feedback"] = response.content.strip()


    return state