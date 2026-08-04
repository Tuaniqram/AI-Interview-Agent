import logging
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from app.graph.interview_state import InterviewState
from app.agents.answer_evaluator_node import answer_evaluator_node
from app.agents.inquisitor_node import inquisitor_node
from app.agents.skill_tracker_node import skill_tracker_node
from app.agents.interview_flow_node import interview_flow_node
from app.agents.decision_node import decision_node

logger = logging.getLogger(__name__)


def _route_after_inquisitor(state: InterviewState) -> str:
    """
    Route to the next node based on inquisitor's decision.
    - "probe" → END (orchestrator will generate follow-up question)
    - "saturate" → skill_tracker → interview_flow → decision → END
    """
    action = state.get('inquisitor_action', 'saturate')
    logger.info(f"Inquisitor routing: action={action}, depth={state.get('question_depth', 0)}")
    if action == 'probe':
        return 'probe_end'
    return 'skill_tracker'


def create_evaluation_workflow():
    """
    Modified evaluation graph with multi-turn follow-up support.

    Flow:
    1. answer_evaluator → Score candidate answer
    2. inquisitor → Decide: probe deeper or saturate?
       - probe: return to orchestrator for follow-up question
       - saturate: continue to flow management
    3. skill_tracker → Extract skills from the answer
    4. interview_flow → Determine next phase/difficulty
    5. decision → Rule-based safety check, finalize
    """
    workflow = StateGraph(InterviewState)

    workflow.add_node("answer_evaluator", answer_evaluator_node)
    workflow.add_node("inquisitor", inquisitor_node)
    workflow.add_node("skill_tracker", skill_tracker_node)
    workflow.add_node("interview_flow", interview_flow_node)
    workflow.add_node("decision", decision_node)

    workflow.set_entry_point("answer_evaluator")

    workflow.add_edge("answer_evaluator", "inquisitor")
    workflow.add_conditional_edges(
        "inquisitor",
        _route_after_inquisitor,
        {
            "probe_end": END,
            "skill_tracker": "skill_tracker",
        }
    )
    workflow.add_edge("skill_tracker", "interview_flow")
    workflow.add_edge("interview_flow", "decision")
    workflow.add_edge("decision", END)

    checkpointer = MemorySaver()
    evaluation_workflow = workflow.compile(checkpointer=checkpointer)

    logger.info("Evaluation workflow compiled with inquisitor routing")
    return evaluation_workflow


_evaluation_workflow = None


def get_evaluation_workflow():
    global _evaluation_workflow
    if _evaluation_workflow is None:
        _evaluation_workflow = create_evaluation_workflow()
    return _evaluation_workflow
