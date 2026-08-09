"""Every load site must reference a prompt file that exists, and every placeholder
a prompt file declares must be supplied by its caller. PromptLoader leaves missing
placeholders as literal {{key}} text, so leftover braces indicate a wiring break."""
import json
import re

import pytest

from app.agents.planning.difficulty_engine import difficulty_governor
from app.agents.generation.question_generator import question_generator_node
from app.agents.planning.strategy_planner import strategy_brain_node
from app.agents.evaluation.synthesis import synthesis_node
from app.agents.evaluation.candidate_evaluator import unified_evaluator_node
from app.agents.decision.hiring_decision import hiring_decision_node
from app.agents.evaluation.evidence_reading import evidence_reading_node
from app.services.prompt_loader import get_prompt_loader
from tests.conftest import EVALUATOR_JSON, GOVERNOR_JSON, STRATEGY_JSON, SYNTHESIS_JSON, make_v4_state

PLACEHOLDER_RE = re.compile(r"\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}")

V4_PROMPTS = [
    "interview/strategy_brain.md",
    "interview/question_generation.md",
    "evaluation/unified_evaluator.md",
    "evaluation/synthesis.md",
    "evaluation/evidence_reading.md",
    "difficulty_governor/difficulty_governor.md",
    "decision/hiring_decision.md",
]

DECISION_JSON = (
    '{"decision": "undecided", "confidence": 0.6, "rationale": "mixed evidence", '
    '"next_steps": ["schedule a short probe round"]}'
)

EVIDENCE_READING_JSON = (
    '{"per_answer": [{"evidence_id": "e1", "claim_classification": "mentioned", '
    '"verifiable": false, "specificity": "low", "ownership": "vague", '
    '"supporting_metric": "", "quote": "I used Kafka."}, '
    '{"evidence_id": "e2", "claim_classification": "proven", "verifiable": true, '
    '"specificity": "high", "ownership": "first_person", '
    '"supporting_metric": "designed the schema", "quote": "I designed the schema."}], '
    '"off_rubric": {"red_flags": [], "hidden_strengths": []}, "semantic_risks": []}'
)


def _leftover(prompt: str) -> list[str]:
    return sorted(set(PLACEHOLDER_RE.findall(prompt)))


def test_v4_prompt_files_exist():
    loader = get_prompt_loader()
    for rel in V4_PROMPTS:
        category, filename = rel.split("/")
        assert (loader.prompts_dir / category / filename).exists(), f"missing: {rel}"


async def test_question_generation_prompt_renders_completely(stub_llm):
    stub = stub_llm(response="Question: Any question?")
    await question_generator_node(make_v4_state())
    prompt = stub.calls[0]["prompt"]
    assert not _leftover(prompt), _leftover(prompt)
    assert "Target Competency" in prompt
    assert "Hypothesis" in prompt


async def test_strategy_brain_prompt_renders_completely(stub_llm):
    stub = stub_llm(response=STRATEGY_JSON)
    await strategy_brain_node(make_v4_state())
    prompt = stub.calls[0]["prompt"]
    assert not _leftover(prompt), _leftover(prompt)


async def test_unified_evaluator_prompt_renders_completely(stub_llm):
    stub = stub_llm(response=json.dumps(EVALUATOR_JSON))
    state = make_v4_state(
        current_question="What is your experience?",
        candidate_answer="I worked on X.",
        question_objective={"target_competency": "tech_core"},
    )
    await unified_evaluator_node(state)
    prompt = stub.calls[0]["prompt"]
    assert not _leftover(prompt), _leftover(prompt)


async def test_synthesis_prompt_renders_completely(stub_llm):
    stub = stub_llm(response=SYNTHESIS_JSON)
    await synthesis_node(make_v4_state(job_role="Software Engineer"))
    prompt = stub.calls[0]["prompt"]
    assert not _leftover(prompt), _leftover(prompt)
    assert "Score Timeline" in prompt


async def test_difficulty_governor_prompt_renders_completely(stub_llm):
    stub = stub_llm(response=GOVERNOR_JSON)
    state = make_v4_state(
        unified_evaluation={
            "technical": {"score": 7.5, "confidence": 0.8},
            "communication": {"score": 6.0, "confidence": 0.7},
        },
        hypothesis_target={"confidence": 0.6, "status": "testing"},
    )
    await difficulty_governor(state, use_llm=True)
    prompt = stub.calls[0]["prompt"]
    assert not _leftover(prompt), _leftover(prompt)
    assert "difficulty change" in prompt.lower()


async def test_evidence_reading_prompt_renders_completely(stub_llm):
    stub = stub_llm(response=EVIDENCE_READING_JSON)
    state = make_v4_state(
        job_role="Backend Engineer",
        evidence_store=[
            {"id": "e1", "evidence_text": "I used Kafka.", "question_number": 1},
            {"id": "e2", "evidence_text": "I designed the schema.", "question_number": 2},
        ],
    )
    result = await evidence_reading_node(state)
    assert result["evidence_reading"]["per_answer"]["e1"]["claim_classification"] == "mentioned"
    prompt = stub.calls[0]["prompt"]
    assert not _leftover(prompt), _leftover(prompt)
    assert "Candidate Answers" in prompt


async def test_hiring_decision_prompt_renders_completely(stub_llm):
    stub = stub_llm(response=DECISION_JSON)
    state = make_v4_state(
        job_role="Backend Engineer",
        final_report={
            "holistic_score": 7.2,
            "fit_assessment": "Good Fit",
            "key_strengths": ["S1"],
            "key_weaknesses": ["W1"],
        },
        hiring_recommendation={"verdict": "hire", "confidence": 0.8, "coverage_ratio": 0.9},
        evidence_store=[{"id": "e1"}, {"id": "e2"}],
    )
    result = await hiring_decision_node(state)
    assert result["hiring_decision"]["decision"] == "insufficient_evidence"
    assert result["hiring_decision"]["decision_scale"] == "7_point"
    assert "decision" not in result["hiring_decision"]["llm_draft"]
    assert "confidence" not in result["hiring_decision"]["llm_draft"]
    prompt = stub.calls[0]["prompt"]
    assert not _leftover(prompt), _leftover(prompt)
    assert "Hiring Decision" in prompt
