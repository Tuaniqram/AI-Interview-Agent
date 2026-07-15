import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.agents.interviewer import interview_agent
from app.agents.evaluator import evaluator_agent
from app.agents.retriever import retrieval_agent

logger = logging.getLogger(__name__)


class InterviewState(TypedDict):
    job_role: str
    question: str
    candidate_answer: str
    company_context: str
    feedback: str


workflow = StateGraph(InterviewState)

workflow.add_node(
    "retriever",
    retrieval_agent
)

workflow.add_node(
    "interviewer",
    interview_agent
)

workflow.add_node(
    "evaluator",
    evaluator_agent
)

workflow.set_entry_point(
    "retriever"
)

workflow.add_edge(
    "retriever",
    "interviewer"
)

workflow.add_edge(
    "interviewer",
    "evaluator"
)

workflow.set_finish_point(
    "evaluator"
)

try:
    graph = workflow.compile()
    logger.info("Workflow compiled successfully")
except Exception as e:
    logger.error(f"Error compiling workflow: {str(e)}")
    raise  