"""InterviewBrain — the V5 persistent reasoning state.

Replaces the flat V4 ``TypedDict`` in ``app/core/interview_state.py`` as the
authoritative state object. Every agent, engine service, store and builder
reads/writes a single ``InterviewBrain``.

Serialization contract:
    ``to_dict()`` produces a dict whose keys match the V4 flat state exactly,
    so the existing ``v4_session_store`` (Memory/Redis + Postgres checkpoint)
    works unchanged. ``from_dict()`` accepts both V5 brain dicts and legacy V4
    state dicts (unknown keys are ignored).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4


@dataclass
class InterviewBrain:
    # -- Identity -----------------------------------------------------------
    brain_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""

    # -- Interview Context --------------------------------------------------
    job_role: str = "Software Engineer"
    department_id: Optional[int] = None
    candidate_id: str = ""
    interview_style: dict = field(default_factory=dict)
    persona: str = "friendly"
    max_questions: int = 14
    flow_type: str = "v5_evidence_driven"

    # -- Conversation State -------------------------------------------------
    current_phase: str = "intro"
    phase_stage: int = 0
    question_number: int = 0
    total_questions: int = 0
    current_question: str = ""
    candidate_answer: str = ""
    conversation_history: list = field(default_factory=list)

    # -- Difficulty ---------------------------------------------------------
    difficulty_level: int = 1
    difficulty_profile: Optional[dict] = None  # V5 6-dimension DifficultyProfile
    difficulty_delta: int = 0
    difficulty_rationale: str = ""
    difficulty_scaffold: str = ""

    # -- Company Intelligence ----------------------------------------------
    company_brain: Optional[dict] = None
    interview_blueprint: Optional[dict] = None
    department_context: list = field(default_factory=list)
    department_requirements: str = ""
    rag_metadata: dict = field(default_factory=dict)

    # -- Candidate Intelligence --------------------------------------------
    candidate_brain: Optional[dict] = None
    initial_hypotheses: list = field(default_factory=list)
    evidence_requirements: list = field(default_factory=list)
    candidate_assessment: dict = field(default_factory=dict)

    # -- Evidence & Memory ---------------------------------------------------
    evidence_store: list = field(default_factory=list)
    evidence_graph: dict = field(default_factory=lambda: {"nodes": {}, "edges": {}})
    candidate_profile: dict = field(default_factory=dict)
    competency_taxonomy: list = field(default_factory=list)
    required_competencies: list = field(default_factory=list)
    domain_label: str = "Technical Knowledge"

    # -- Hypotheses ---------------------------------------------------------
    hypotheses: list = field(default_factory=list)
    hypothesis_target: Optional[dict] = None
    hypothesis_state: dict = field(default_factory=dict)

    # -- Competency Planning ------------------------------------------------
    competency_plan: list = field(default_factory=list)
    planned_competency: Optional[dict] = None
    next_competency: Optional[dict] = None
    competency_summary: dict = field(default_factory=dict)

    # -- Strategy -----------------------------------------------------------
    interview_strategy: Optional[dict] = None
    strategy_cache_valid: bool = False

    # -- AURA Brain V5 ------------------------------------------------------
    aura_brain: Optional[dict] = None
    role_brain: Optional[dict] = None
    competency_graph: dict = field(default_factory=dict)
    uncertainty_map: dict = field(default_factory=dict)
    question_strategy: Optional[dict] = None
    calibration_state: Optional[dict] = None
    contradiction_state: dict = field(default_factory=dict)
    difficulty_state: dict = field(default_factory=dict)
    decision_state: Optional[dict] = None
    candidate_memory: dict = field(default_factory=dict)
    brain_utilization: dict = field(default_factory=dict)  # per-layer live usage
    evidence_cursor: dict = field(default_factory=dict)    # typed-graph targeting cursor
    conclusive_turns: int = 0                              # runs of decisive calibration turns

    # -- Evaluation ---------------------------------------------------------
    unified_evaluation: Optional[dict] = None
    evaluator_mode: str = "unified"
    evaluation_score: Optional[float] = None
    extracted_evidence: list = field(default_factory=list)
    evaluation_failed: bool = False
    skip_evaluation: bool = False
    score_reasons: list = field(default_factory=list)          # explainable scoring
    score_contributions: list = field(default_factory=list)    # explainable scoring

    # -- Reflection & Decision ----------------------------------------------
    reflection_action: str = "probe"
    director: dict = field(default_factory=dict)  # latest director decision
    consecutive_probes: int = 0
    last_hypothesis_target_id: str = ""
    hiring_recommendation: dict = field(default_factory=dict)
    hiring_decision: dict = field(default_factory=dict)
    decision_review: dict = field(default_factory=dict)  # self-review trail
    evidence_sufficiency: dict = field(default_factory=dict)
    reflection_inputs: dict = field(default_factory=dict)  # coverage/conf/difficulty/budget
    contradictions: list = field(default_factory=list)
    consistency_checks: list = field(default_factory=list)
    observations: list = field(default_factory=list)
    claim_signals: dict = field(default_factory=dict)  # F5 authenticity signals

    # -- Question Objective -------------------------------------------------
    question_objective: Optional[dict] = None
    conversation_turn: Optional[dict] = None
    questions_asked: list = field(default_factory=list)
    answered_question_numbers: list = field(default_factory=list)

    # -- Metadata -----------------------------------------------------------
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    nodes_executed: list = field(default_factory=list)
    state_version: int = 0

    # ------------------------------------------------------------------ #
    # Serialization / compatibility
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Serialize to a dict matching the V4 flat-state key structure."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @classmethod
    def from_dict(cls, data: dict) -> "InterviewBrain":
        """Deserialize from a V5 brain dict or a legacy V4 state dict.

        Accepts every key (agents add ad-hoc fields like ``conversation_turn``
        that are not declared dataclass fields) so a mid-interview reload never
        loses data.
        """
        brain = cls()
        for k, v in data.items():
            setattr(brain, k, v)
        brain.brain_id = brain.brain_id or str(uuid4())
        return brain

    def sync_from_dict(self, state: dict) -> "InterviewBrain":
        """Pull any fields that changed inside a plain-dict agent pass back in."""
        for k, v in state.items():
            if hasattr(self, k):
                setattr(self, k, v)
        return self

    def sync_to_dict(self, state: dict) -> dict:
        """Push brain fields into a plain dict for a legacy agent pass."""
        for k, v in self.to_dict().items():
            state[k] = v
        return state

    # ------------------------------------------------------------------ #
    # Timeline / graph helpers
    # ------------------------------------------------------------------ #

    def to_event(self, event_type: str, payload: Optional[dict] = None) -> dict:
        """Build an ``interview_timeline`` row for the current brain state."""
        return {
            "session_id": self.session_id,
            "event_type": event_type,
            "event_data": payload or {},
            "brain_version": self.state_version,
            "question_number": self.question_number,
        }

    def bump_version(self) -> None:
        self.state_version += 1

    # ------------------------------------------------------------------ #
    # Evidence graph convenience
    # ------------------------------------------------------------------ #

    def add_evidence_edge(
        self,
        evidence_id: str,
        hypothesis_id: str,
        weight: float,
        support: bool = True,
    ) -> None:
        """Record an evidence→hypothesis edge in the evidence graph."""
        edge_id = f"{evidence_id}->{hypothesis_id}"
        self.evidence_graph.setdefault("edges", {})[edge_id] = {
            "source": evidence_id,
            "target": hypothesis_id,
            "weight": round(float(weight), 4),
            "support": support,
        }

    def set_competency_score(self, competency_id: str, score: float, weight: float = 1.0) -> None:
        """Track a competency node in the evidence graph (for the final report)."""
        self.evidence_graph.setdefault("nodes", {})[competency_id] = {
            "type": "competency",
            "score": round(float(score), 4),
            "weight": float(weight),
        }
