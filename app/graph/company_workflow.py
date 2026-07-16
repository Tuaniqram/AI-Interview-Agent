import logging

from typing import TypedDict

from langgraph.graph import StateGraph

from app.company_agents.company_retriever import company_retriever
from app.company_agents.company_interviewer import company_interviewer
from app.company_agents.company_evaluator import company_evaluator


logger = logging.getLogger(__name__)


class CompanyInterviewState(TypedDict):

    company_id:int

    job_role:str

    question:str

    candidate_answer:str

    company_context:str

    feedback:str



workflow = StateGraph(
    CompanyInterviewState
)



workflow.add_node(
    "company_retriever",
    company_retriever
)


workflow.add_node(
    "company_interviewer",
    company_interviewer
)


workflow.add_node(
    "company_evaluator",
    company_evaluator
)



workflow.set_entry_point(
    "company_retriever"
)



workflow.add_edge(
    "company_retriever",
    "company_interviewer"
)


workflow.add_edge(
    "company_interviewer",
    "company_evaluator"
)



workflow.set_finish_point(
    "company_evaluator"
)



company_graph = workflow.compile()