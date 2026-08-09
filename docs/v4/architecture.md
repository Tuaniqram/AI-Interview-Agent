# AI Interview Engine v4 — Evidence-Driven Architecture

> **Core shift**: "What question should I ask next?" → **"What evidence do I still need before making a hiring decision?"**
>
> Every question exists to fill a specific evidence gap. The interview ends when sufficient evidence is collected across all required competencies.

**Inherits from v3**: multi-turn probing, skill tracker, phase-aware RAG, holistic synthesis, company RAG, Pinecone, Supabase, FastAPI backend, React frontend — nothing removed.

---

## Table of Contents

1. [Philosophy & Key Concepts](#1-philosophy--key-concepts)
2. [Architecture Overview](#2-architecture-overview)
3. [Node Architecture](#3-node-architecture)
4. [Competency Taxonomy](#4-competency-taxonomy)
5. [Interview Styles](#5-interview-styles)
6. [Data Models](#6-data-models)
7. [New DB Schemas](#7-new-db-schemas)
8. [Nested LangGraph Subgraphs](#8-nested-langgraph-subgraphs)
9. [Unified Evaluator](#9-unified-evaluator)
10. [Hypothesis Manager](#10-hypothesis-manager)
11. [Observation Layer](#11-observation-layer)
12. [Prompt Strategy](#12-prompt-strategy)
13. [API Changes](#13-api-changes)
14. [Migration Plan — 6 Phases](#14-migration-plan--6-phases)
15. [Directory Structure After v4](#15-directory-structure-after-v4)
16. [Appendix: State Field Reference](#16-appendix-state-field-reference)

---

## 1. Philosophy & Key Concepts

### The Evidence Gap

In v3, the engine asks: *"What question should I ask next?"* It generates a question, the candidate answers, it's evaluated, and the cycle repeats. Problem: **question generation is disconnected from hiring decisions.**

v4 plans every question backward from the evidence needed:

```
Hiring Decision
    └── What evidence is needed?
            └── Which competencies are unproven?
                    └── What evidence gaps remain per competency?
                            └── What question fills this gap?
                                    └── Ask question → extract evidence
                                            └── Evidence stored → gaps re-evaluated
                                                    └── Decision: more evidence or hire/no-hire?
```

### Hypothesis-Based Interviewing

Real interviewers don't just collect evidence — they constantly form and test **hypotheses** about the candidate. Every answer either strengthens or weakens those hypotheses. This is the key architectural insight that sets v4 apart.

```
Initial hypotheses (from resume + job req):
  - "Strong Laravel"          confidence: 0.0
  - "Weak Database"           confidence: 0.0
  - "Good Communicator"       confidence: 0.0
  - "Average Architecture"    confidence: 0.0

After answer #1 (Laravel question):
  - "Strong Laravel"          confidence: 0.85  ↑
  - "Weak Database"           confidence: 0.0   (untouched)
  - "Good Communicator"       confidence: 0.70  ↑
  - "Average Architecture"    confidence: 0.0   (untouched)

Next question targets the most uncertain hypothesis:
  → "Weak Database" (confidence 0.0 — completely untested)
```

### Key Concepts

| Concept | Definition |
|---------|-----------|
| **Evidence** | A scored, categorized observation from a candidate answer, with **confidence** (0.0-1.0) |
| **Evidence Dimension** | One of 6 evaluative lenses: Technical, Communication, Reasoning, Behavioral, Confidence, Completeness |
| **Competency** | A hiring requirement (e.g., "Python Proficiency") — maps to one or more evidence dimensions |
| **Evidence Gap** | Delta between evidence collected and evidence required for a competency |
| **Hypothesis** | A belief about the candidate with a confidence score, updated Bayesian-style per answer |
| **Interview Strategy** | The overall plan: which hypotheses to test, which competencies to prioritize — cached and only re-run on key triggers |
| **Interview Style** | A configurable profile that defines competency priorities, personas, probe depth, evaluator weights |
| **Observation** | Non-scoring signals: verbosity, hedging, certainty shifts, emotional changes — extracted from text |

---

## 2. Architecture Overview

### 2.1 High-Level Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (React)                          │
│  InterviewRoom → interviewStore → interviewController → REST/WS     │
└────────────────────────────────────┬─────────────────────────────────┘
                                     │
┌────────────────────────────────────┴─────────────────────────────────┐
│                        API LAYER (FastAPI)                           │
│  POST /interviews/v4/start           POST /interviews/v4/answer      │
│  POST /interviews/v4/next-question   GET  /interviews/v4/evidence    │
│  GET  /interviews/v4/status          GET  /interviews/v4/decision    │
└────────────────────────────────────┬─────────────────────────────────┘
                                     │
┌────────────────────────────────────┴─────────────────────────────────┐
│                   INTERVIEW SUPERVISOR (top-level graph)             │
│                                                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐             │
│  │ Candidate    │   │ Company      │   │ Interview    │             │
│  │ Profile      │   │ Knowledge    │   │ Strategy     │ (cached)    │
│  │ Loader       │   │ Loader       │   │ (LLM, 1x)    │             │
│  └──────────────┘   └──────────────┘   └──────┬───────┘             │
│                                                │                    │
│                                                ▼                    │
│                                       ┌──────────────┐             │
│                                       │ Competency   │             │
│                                       │ Planner      │ (no LLM)  │
│                                       └──────┬───────┘             │
│                                                │                    │
│                                                ▼                    │
│                                       ┌──────────────┐             │
│                                       │ Hypothesis   │             │
│                                       │ Manager      │             │
│                                       └──────┬───────┘             │
│                                                │                    │
│                          ┌─────────────────────┴─────────────┐      │
│                          │         MAIN LOOP (cyclic)        │      │
│                          │                                    │      │
│                          │  ┌────────────────────────────┐    │      │
│                          │  │   QUESTION SUBGRAPH        │    │      │
│                          │  │  ┌──────────────────┐      │    │      │
│                          │  │  │ Question Planner │      │    │      │
│                          │  │  └────────┬─────────┘      │    │      │
│                          │  │           ▼                │    │      │
│                          │  │  ┌──────────────────┐      │    │      │
│                          │  │  │ Question Gen     │      │    │      │
│                          │  │  │ (persona-aware)  │      │    │      │
│                          │  │  └──────────────────┘      │    │      │
│                          │  └──────────┬─────────────────┘    │      │
│                          │             │                      │      │
│                          │             ▼                      │      │
│                          │  ┌────────────────────────────┐    │      │
│                          │  │   EVALUATION SUBGRAPH      │    │      │
│                          │  │  ┌──────────────────┐      │    │      │
│                          │  │  │ Unified Evaluator│      │    │      │
│                          │  │  │ (1 LLM call,     │      │    │      │
│                          │  │  │  6 dimensions)   │      │    │      │
│                          │  │  └────────┬─────────┘      │    │      │
│                          │  │           ▼                │    │      │
│                          │  │  ┌──────────────────┐      │    │      │
│                          │  │  │ Evidence          │      │    │      │
│                          │  │  │ Extractor         │      │    │      │
│                          │  │  └──────────────────┘      │    │      │
│                          │  └──────────┬─────────────────┘    │      │
│                          │             │                      │      │
│                          │             ▼                      │      │
│                          │  ┌────────────────────────────┐    │      │
│                          │  │   REFLECTION SUBGRAPH      │    │      │
│                          │  │  ┌──────────────────┐      │    │      │
│                          │  │  │ Consistency      │      │    │      │
│                          │  │  │ Checker          │      │    │      │
│                          │  │  └────────┬─────────┘      │    │      │
│                          │  │           ▼                │    │      │
│                          │  │  ┌──────────────────┐      │    │      │
│                          │  │  │ Observation      │      │    │      │
│                          │  │  │ Analyzer         │      │    │      │
│                          │  │  └────────┬─────────┘      │    │      │
│                          │  │           ▼                │    │      │
│                          │  │  ┌──────────────────┐      │    │      │
│                          │  │  │ Reflection       │      │    │      │
│                          │  │  │ Engine           │      │    │      │
│                          │  │  └──────────────────┘      │    │      │
│                          │  └────────────────────────────┘    │      │
│                          │                                    │      │
│                          └──────────────────┬─────────────────┘      │
│                                                │                    │
│                          ┌─────────────────────┴─────────────┐      │
│                          │   Action Router                    │      │
│                          │   probe | change_competency |      │      │
│                          │   increase_difficulty | finish    │      │
│                          └───────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Differences from v3

| Aspect | v3 | v4 |
|--------|----|----|
| Graphs | 2 separate (question + evaluation) | 3 nested subgraphs under Interview Supervisor |
| Question trigger | "Ask next question" | "Fill this evidence gap" |
| Evaluation | Single answer_evaluator (2 scores) | Unified Evaluator (6 dimensions, 1 LLM call) |
| Parallel evaluators | Not available | Optional (enterprise/research mode only) |
| Memory | Session-only | Structured CandidateProfile (persistent) |
| Competency model | Skills list (flat) | Hierarchical taxonomy, deterministic planner |
| Evidence store | Implicit (in messages + evaluations) | Explicit + aggregated CompetencySummary |
| Consistency | Not checked | Built into reflection subgraph |
| Probes | Inquisitor node (heuristic, score-based) | Hypothesis-driven: most uncertain → probe |
| Interview style | N/A (one-size-fits-all) | 11 styles + 7 personas |
| Strategy | Recalculated every turn | Cached, invalidated on triggers |
| Hypotheses | None | First-class: Bayesian belief update |
| Observations | None | Extracted per answer (hedging, verbosity, etc.) |
| Confidence | Not tracked | Per-evidence confidence score |
| Debugging | Single monolithic graph | 3 independent subgraphs, testable in isolation |

---

## 3. Node Architecture

### 3.1 Context Group (runs once per session)

#### 1. Candidate Profile Loader

**File**: `app/agents/candidate_profile_node.py` (NEW)

**Purpose**: Load and update a structured `CandidateProfile` across sessions. **Not** a generic key-value store — a typed schema with per-competency scores, strengths, weaknesses, risk flags, and contradictions.

**Profile structure**:
```python
CandidateProfile:
    candidate_id: str
    technical: Dict[str, float]       # competency → score
    communication: Dict[str, float]
    behavioral: Dict[str, float]
    leadership: Dict[str, float]
    architecture: Dict[str, float]
    debugging: Dict[str, float]
    ownership: Dict[str, float]
    learning: Dict[str, float]
    confidence: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    risk_flags: List[Dict]            # {flag, severity, evidence_text}
    contradictions: List[Dict]        # cross-session contradictions
    evidence_summary: Dict[str, Dict] # competency → {count, avg_score, last_score}
    session_count: int
    last_updated: datetime
```

**Logic**:
1. Load `profile_data` JSONB from `candidate_profiles` table
2. Parse into `CandidateProfile` struct
3. After each answer: update profile with new evidence (update scores, append strengths/weaknesses)
4. Save back to DB (throttled: save every 3 answers, not every answer)

#### 2. Company Knowledge Loader

**File**: `app/agents/company_context_node.py` (v3, enhanced)

**Purpose**: Retrieve RAG context for the current department/phase. **Unchanged from v3** — already phase-aware, already caches results.

**Enhancements for v4**: Also retrieves company-wide competency requirements from a new `competency_requirements` Pinecone namespace.

### 3.2 Planning Group (runs at session start + on triggers)

#### 3. Interview Strategy Brain

**File**: `app/agents/strategy_brain_node.py` (NEW — LLM, but cached)

**Purpose**: Set the high-level interview strategy. **Runs once at session start, then cached.** Re-runs only on specific triggers.

**Triggers to re-run** (check each loop iteration):
- Phase changes
- Contradiction found
- Difficulty changes
- Major evidence gap closes (>50% reduction)

**Inputs**: Job role, interview style, company requirements, candidate profile, competency taxonomy

**Outputs**:
```python
{
    "phase_order": List[str],          # e.g., ["intro", "technical", "behavioral", "conclusion"]
    "competency_priority": Dict[str, str],  # competency_id → HIGH/MEDIUM/LOW
    "difficulty_range": (int, int),    # (min, max)
    "persona": str,                    # selected persona for this session
    "strategic_intent": str,           # e.g., "Verify Laravel strength, stress-test DB knowledge"
    "early_termination_threshold": float, # if all competencies above this → finish
}
```

**Prompt**: `prompts/interview/strategy_brain.md`

#### 4. Competency Planner

**File**: `app/agents/competency_planner.py` (NEW — **pure Python, no LLM**)

**Purpose**: Compute which competencies need attention. Deterministic — no LLM call.

**Logic**:
```python
def plan(evidence_summary, style, strategy):
    results = []
    for comp in taxonomy:
        required = style.evidence_minimums.get(comp.id, 2)
        collected = evidence_summary.get(comp.id, {}).get("evidence_count", 0)
        gap = 1.0 - (collected / required)
        priority = strategy.competency_priority.get(comp.id, "LOW")
        results.append({
            "id": comp.id,
            "gap": gap,
            "priority": priority,
            "dimension": comp.evidence_dimensions[0]  # primary dimension
        })
    # Sort: HIGH priority first, then by gap descending
    # Ties broken by: which competency has been least recently tested
    # LLM only called if priority ties AND gap ties (extremely rare)
    return sort_by_priority_then_gap(results)
```

**Output**: Ordered list of competencies needing evidence, each with gap score.

#### 5. Hypothesis Manager

**File**: `app/agents/hypothesis_manager.py` (NEW)

**Purpose**: Manage and update beliefs about the candidate. Each hypothesis has a **confidence score** (0.0-1.0) updated after every answer.

This is the core innovation: questions target the **most uncertain** hypothesis, not just the largest gap.

**Initial hypothesis generation** (at session start):
```python
from resume + job_requirements + candidate_profile:
  - "Strong {skill}" for each skill in resume
  - "Weak {skill}" for each skill in job_req but missing in resume
  - "Good communicator" (default)
  - "Average architecture" (default)
  - "Fast learner" (if career shifts present)
  All start at confidence: 0.0 (untested)
```

**Updating** (after each evidence extraction):
```python
def update_hypotheses(hypotheses, evidence_list):
    for evidence in evidence_list:
        for hypothesis in hypotheses:
            relevance = compute_relevance(hypothesis, evidence)  # 0.0-1.0
            if relevance < 0.3:
                continue
            # Simple Bayesian-ish update
            delta = (evidence.score / 10.0) * relevance * 0.3
            # evidence_score 8/10 * relevance 0.9 * learning_rate 0.3 = +0.216
            if hypothesis.direction == "positive":  # e.g., "Strong Laravel"
                hypothesis.confidence += delta if evidence.score >= 5 else -delta
            else:  # "Weak Database"
                hypothesis.confidence += delta if evidence.score < 5 else -delta
            hypothesis.confidence = clamp(hypothesis.confidence, 0.0, 1.0)
            (hypothesis.supporting if delta > 0 else hypothesis.contradicting).append(evidence.id)
```

**Selecting next target**:
```python
def next_target(hypotheses):
    # The hypothesis closest to 0.5 is the most uncertain → probe it
    return min(hypotheses, key=lambda h: abs(h.confidence - 0.5))
```

This transforms interviewing from evidence collection into **Bayesian reasoning** — maintaining and updating beliefs as new evidence arrives.

### 3.3 Question Subgraph (entry per loop iteration)

#### 6. Question Planner

**File**: `app/agents/question_planner_node.py` (NEW — lightweight LLM)

**Inputs**: Target hypothesis (from Hypothesis Manager), competency gaps, conversation history, phase, persona

**Outputs**: `question_objective`:
```python
{
    "target_hypothesis": "weak_database",
    "target_competency": "tech_db",
    "target_dimension": "technical",
    "probe_depth": 0,                     # 0 = new topic, 1+ = follow-up
    "question_type": "open_ended",       # open_ended | probing | hypothetical | behavioral | technical
    "hypothesis_to_test": "Candidate has weak database knowledge",  # verbatim
    "current_confidence": 0.62,
    "success_criteria": "Evidence of SQL query optimization understanding"
}
```

**Prompt**: `prompts/interview/question_planner.md`

#### 7. Question Generator

**File**: `app/agents/question_generation_node.py` (v3, adapted)

**Inputs**: Question objective, company context, candidate profile, conversation history, phase, **persona**

**Persona integration**: The prompt receives a `persona` directive from the interview style:
- `"friendly"` → warm, encouraging, "Can you tell me about..."
- `"formal"` → structured, precise, "Describe your experience with..."
- `"strict"` → terse, direct, "Explain how..."
- `"faang"` → algorithmic, pressured, "Design a solution for..."
- `"conversational"` → natural, casual, "So how did that work out?"
- `"stress"` → confrontational, interrupting, "That's not what I asked. Try again."
- `"mentor"` → guiding, Socratic, "What would happen if you tried X instead?"

**Output**: `current_question` — the question text, persona-adapted.

**Prompt**: `prompts/interview/question_generation.md` (updated for persona + hypothesis)

### 3.4 Evaluation Subgraph (per answer)

#### 8. Unified Evaluator

**File**: `app/agents/unified_evaluator_node.py` (NEW — replaces parallel evaluators)

**Purpose**: **Single LLM call** evaluating all 6 dimensions. Returns structured JSON with scores, evidence, confidence, and observations. This is the default mode — cost-efficient and fast.

**Enterprise/Research mode**: Configurable `evaluator_mode: "parallel"` on the interview style re-enables 6 independent evaluators. Default is `"unified"`.

**Inputs**: Question, answer, conversation history, competency context, persona, difficulty

**Output** (single JSON):
```python
{
    "technical": {
        "score": 8.5,
        "evidence": "Explained async/await mechanics correctly...",
        "confidence": 0.9,
        "strengths": ["Deep async understanding", "Error handling awareness"],
        "weaknesses": ["Missing edge case discussion"]
    },
    "communication": {
        "score": 7.0,
        "evidence": "Answer was structured but rambled midway...",
        "confidence": 0.85,
        "strengths": ["Good opening structure"],
        "weaknesses": ["Lost clarity in middle section"]
    },
    "reasoning": {
        "score": 9.0,
        "evidence": "Considered three alternative approaches...",
        "confidence": 0.95,
        "strengths": ["Systematic elimination", "Trade-off analysis"],
        "weaknesses": []
    },
    "behavioral": {
        "score": 6.5,
        "evidence": "Described solo work, limited team interaction...",
        "confidence": 0.6,
        "strengths": ["Took ownership"],
        "weaknesses": ["No team collaboration mentioned"]
    },
    "confidence": {
        "score": 8.0,
        "evidence": "Spoke with certainty on main points, acknowledged unknowns...",
        "confidence": 0.8
    },
    "completeness": {
        "score": 7.5,
        "evidence": "Covered 3 of 4 sub-parts of the question...",
        "confidence": 0.85
    },
    "observations": {                         # ← NEW: observation layer
        "verbosity": 0.6,                      # 0=terse, 1=rambling
        "hedging": 0.2,                        # 0=direct, 1=uncertain ("I think", "maybe")
        "certainty_shift": -0.1,               # +/- change in certainty from previous answer
        "sentiment_shift": "neutral",          # "positive" | "neutral" | "defensive" | "excited"
        "response_latency_estimate": "medium", # "quick" | "medium" | "hesitant" | "very_hesitant"
        "notable_patterns": [
            "Candidate became more technical when discussing database topics",
            "Candidate used filler words when describing conflict resolution"
        ]
    },
    "composite_score": 7.85,  # weighted by interview style
    "evaluator_mode": "unified"  # or "parallel" if enterprise mode
}
```

**Performance**: 1 LLM call per answer. For 15 questions → 15 calls (vs 90 in the parallel approach).

**Prompt**: `prompts/evaluation/unified_evaluator.md`

#### 9. Evidence Extractor

**File**: `app/agents/evidence_extractor_node.py` (NEW)

**Inputs**: Unified evaluation output, question, answer, question objective

**Logic**:
1. Parse each dimension's score + evidence into structured evidence items
2. Map each to a competency from the taxonomy
3. Store in `evidence_store` table
4. Update `competency_summary` (in-memory + DB cache)
5. Update `CandidateProfile` (strengths, weaknesses, per-competency scores)
6. Push evidence to `HypothesisManager` for belief update

**Output**: `extracted_evidence` — list of evidence items, each with:
```python
{
    "id": "uuid",
    "dimension": "technical",
    "competency": "tech_db",
    "score": 8.5,
    "confidence": 0.9,          # from unified evaluator
    "evidence_text": "...",
    "source_question": "...",
    "question_number": 5,
    "hypothesis": "weak_database",
    "hypothesis_relevance": 0.85
}
```

**Prompt**: `prompts/interview/evidence_extractor.md`

### 3.5 Reflection Subgraph (post-evaluation)

#### 10. Consistency Checker

**File**: `app/agents/consistency_checker_node.py` (NEW)

**Inputs**: Current evidence, past evidence from this session, candidate profile (cross-session), conversation history

**Outputs**:
```python
{
    "contradictions": [
        {
            "dimension": "technical",
            "previous_claim": "Said MongoDB is their primary DB",
            "current_claim": "Said they use PostgreSQL exclusively",
            "severity": "high"
        }
    ],
    "growth_signals": [
        "Score improved from 5.0 to 8.0 on database questions across the session"
    ],
    "consistency_score": 0.85   # 0.0-1.0
}
```

**Logic**: LLM-based comparison with targeted prompt. High-severity contradictions invalidate the strategy brain cache.

**Prompt**: `prompts/interview/consistency_checker.md`

#### 11. Observation Analyzer

**File**: `app/agents/observation_analyzer.py` (NEW)

**Purpose**: Extract non-scoring signals from the answer that human interviewers naturally notice.

**Inputs**: Unified evaluator's `observations` field, previous observations from same session, conversation history

**Outputs**:
```python
{
    "verbosity_trend": "increasing",     # candidate getting more verbose over time
    "hedging_trend": "stable",
    "certainty_trend": "improving",
    "emotional_state": "engaged",        # "engaged" | "defensive" | "anxious" | "excited" | "fatigued"
    "notable_events": [
        "Became defensive when pressed on SQL optimization",
        "Showed visible excitement discussing system design"
    ],
    "risk_signals": [
        {
            "signal": "defensive_response",
            "evidence": "Interrupted the question to justify their approach",
            "severity": "medium"
        }
    ]
}
```

**No LLM call needed** — observations are already extracted by the unified evaluator. This node aggregates and trends them.

**Prompt**: None (aggregation logic only)

#### 12. Reflection Engine

**File**: `app/agents/reflection_engine.py` (NEW — **merged Reflection + Decision**)

**Purpose**: Decide what to do next. Single responsibility, single LLM call. Replaces both the v3 inquisitor and the separate reflection + decision nodes.

**Inputs**:
- Evidence gaps (from Competency Planner)
- Hypotheses with confidences (from Hypothesis Manager)
- Consistency checks
- Observation trends
- Probe depth on current topic
- Interview style config
- Strategy (cached)

**Output**:
```python
{
    "action": "probe",                    # "probe" | "change_competency" | "increase_difficulty" | "finish"
    "target_competency": "tech_db",       # only if action == "change_competency"
    "reasoning": "Database hypothesis confidence 0.62 is most uncertain",  # explainable
    "evidence_sufficiency": 0.73,         # % of required evidence collected
    "hiring_readiness": "not_yet"         # "ready" | "not_yet" | "early_termination_possible"
}
```

**Decision logic** (LLM-guided, but with guardrails):
```
IF evidence_sufficiency >= style.early_termination_threshold AND
   all HIGH priority competencies have evidence_count >= minimum:
   → "finish" with early_termination_possible

IF observation_analyzer detected defensive_pattern AND
   current persona == "stress":
   → "change_competency" (de-escalate, switch to safe topic)

IF hypothesis with confidence closest to 0.5 is same as current competency AND
   probe_depth < style.max_probe_depth:
   → "probe"

IF all HIGH priority competencies have gap < 0.2 AND
   all hypothesis confidences are > 0.8 OR < 0.3:
   → "finish"

ELSE:
   → "change_competency" (next most uncertain hypothesis)
```

**Prompt**: `prompts/interview/reflection_engine.md`

### 3.6 Action Router (graph routing)

#### 13. Action Router

**File**: `app/agents/action_router.py` (NEW)

**Purpose**: Direct graph flow based on Reflection Engine output. No LLM, no logic — pure routing.

| Reflection Action | Graph Route |
|-------------------|-------------|
| `probe` | → Question Subgraph (depth+1, same competency) |
| `change_competency` | → Competency Planner → Hypothesis Manager → Question Subgraph |
| `increase_difficulty` | → Update state difficulty → Question Subgraph |
| `finish` | → Synthesis → END |

---

## 4. Competency Taxonomy

### 4.1 Competency Definitions

| ID | Name | Category | Evidence Dimensions | Default Min Evidence |
|----|------|----------|-------------------|---------------------|
| `tech_core` | Core Language Proficiency | technical | technical, completeness | 2 |
| `tech_framework` | Framework & Library Knowledge | technical | technical, confidence | 2 |
| `tech_system_design` | System Design & Architecture | technical | technical, reasoning | 3 |
| `tech_data` | Data Structures & Algorithms | technical | technical, reasoning | 2 |
| `tech_db` | Database & Storage | technical | technical, completeness | 2 |
| `tech_devops` | DevOps & Infrastructure | technical | technical, confidence | 1 |
| `tech_testing` | Testing & Quality | technical | technical, completeness | 1 |
| `tech_security` | Security Practices | technical | technical, reasoning | 1 |
| `behav_teamwork` | Teamwork & Collaboration | behavioral | behavioral, communication | 2 |
| `behav_leadership` | Leadership & Ownership | behavioral | behavioral, confidence | 2 |
| `behav_conflict` | Conflict Resolution | behavioral | behavioral, reasoning | 2 |
| `behav_communication` | Communication Clarity | behavioral | communication, completeness | 1 |
| `behav_adaptability` | Adaptability & Learning | behavioral | behavioral, confidence | 1 |
| `cog_problem_solving` | Problem Solving | cognitive | reasoning, technical | 2 |
| `cog_analytical` | Analytical Thinking | cognitive | reasoning, completeness | 2 |
| `cog_creativity` | Creativity & Innovation | cognitive | reasoning, behavioral | 1 |
| `cog_decision_making` | Decision Making | cognitive | reasoning, confidence | 2 |
| `exp_project_depth` | Project Depth & Impact | experience | technical, completeness | 2 |
| `exp_domain` | Domain Knowledge | experience | technical, confidence | 2 |
| `exp_scaling` | Scale & Complexity Experience | experience | technical, reasoning | 2 |

### 4.2 Competency Summary (derived, not stored as rows)

For fast reads without scanning all evidence rows:

```python
competency_summary: Dict[str, Dict] = {
    "tech_db": {
        "evidence_count": 3,
        "average_confidence": 0.87,
        "average_score": 7.8,
        "latest_score": 8.5,
        "latest_evidence": "Explained query optimization, mentioned indexing strategies",
        "coverage": 0.75,           # evidence_count / required_minimum
        "gap": 0.25                 # 1.0 - coverage
    },
    ...
}
```

Updated after every evidence extraction. Read by Competency Planner (no scan needed).

---

## 5. Interview Styles

### 5.1 Definition

```python
@dataclass
class InterviewStyle:
    name: str
    persona: str                            # "friendly" | "formal" | "strict" | "faang" | "conversational" | "stress" | "mentor"
    evaluator_mode: str                     # "unified" (default) | "parallel" (enterprise/research)
    base_competency_priority: Dict[str, str] # competency_id → HIGH/MEDIUM/LOW
    evidence_minimums: Dict[str, int]        # competency_id → min evidence count
    evaluator_weights: Dict[str, float]      # dimension → weight for composite score
    max_probe_depth: int
    phase_order: List[str]
    early_termination_threshold: float       # 0.0-1.0 (evidence sufficiency %)
    difficulty_range: Tuple[int, int]
    max_questions: int
    allow_probing: bool
    hypothesis_count: int                    # how many active hypotheses to maintain
```

### 5.2 Predefined Styles

| Style | Persona | Evaluator Mode | Focus | Max Depth | Key Competencies |
|-------|---------|---------------|-------|-----------|-----------------|
| **FRESH_GRAD** | mentor | unified | Core + DSA + Learning | 1 | tech_core, tech_data, behav_adaptability |
| **JUNIOR** | friendly | unified | Framework + Team + Growth | 2 | tech_framework, behav_teamwork, tech_testing |
| **MID_LEVEL** | conversational | unified | All tech + System Design + Ownership | 3 | tech_core, tech_framework, tech_system_design, behav_leadership |
| **SENIOR** | formal | unified | Architecture + Leadership + Impact | 3 | tech_system_design, behav_leadership, cog_decision_making, exp_scaling |
| **TECH_LEAD** | formal | unified | Leadership + Architecture + People | 3 | behav_leadership, behav_teamwork, tech_system_design, cog_decision_making |
| **EM** | formal | unified | Leadership + Process + Strategy | 2 | behav_leadership, behav_conflict, cog_decision_making, exp_best_practices |
| **FAANG** | faang | parallel | DSA + System Design + Depth | 4 | tech_data, tech_system_design, cog_problem_solving, cog_analytical |
| **FAANG_LITE** | faang | unified | Same as FAANG but cost-optimized | 3 | same |
| **STARTUP** | conversational | unified | Full-stack + Adaptability + Speed | 2 | tech_core, tech_framework, behav_adaptability, exp_project_depth |
| **CONTRACT** | formal | unified | Domain + Delivery + Independence | 1 | exp_domain, exp_project_depth, behav_communication |
| **EXECUTIVE** | formal | unified | Strategy + Vision + Leadership | 2 | behav_leadership, cog_decision_making, cog_creativity, exp_scaling |
| **STRESS_TEST** | stress | unified | Resilience + Pressure Handling | 3 | behav_adaptability, behav_conflict, cog_problem_solving |
| **STANDARD** | friendly | unified | Balanced across all competencies | 2 | All competencies, balanced weights |

---

## 6. Data Models

### 6.1 Evidence

```python
@dataclass
class Evidence:
    id: str                            # UUID
    session_id: str                    # FK to interview_sessions
    dimension: str                     # "technical" | "communication" | "reasoning" | "behavioral" | "confidence" | "completeness"
    competency: str                    # competency_id from taxonomy
    score: float                       # 0.0-10.0
    confidence: float                  # 0.0-1.0 — how reliable is this evidence
    evidence_text: str                 # extracted observation
    source_question: str               # the question that produced this evidence
    question_number: int
    hypothesis_id: str                 # which hypothesis this evidence relates to (optional)
    hypothesis_relevance: float        # 0.0-1.0
    metadata: dict                     # extra context
    created_at: datetime
```

### 6.2 CandidateProfile

```python
@dataclass
class CandidateProfile:
    candidate_id: str
    technical: Dict[str, float]        # competency → average score
    communication: Dict[str, float]
    behavioral: Dict[str, float]
    leadership: Dict[str, float]
    architecture: Dict[str, float]
    debugging: Dict[str, float]
    ownership: Dict[str, float]
    learning: Dict[str, float]
    confidence_trait: Dict[str, float]  # behavioral confidence, not score
    strengths: List[str]
    weaknesses: List[str]
    risk_flags: List[Dict]             # [{flag, severity, evidence, session_id}]
    contradictions: List[Dict]         # [{claim_a, claim_b, dimension, session_id}]
    evidence_summary: Dict[str, Dict]  # competency → {count, avg_score, last_score, avg_confidence}
    session_count: int
    last_updated: datetime
```

### 6.3 Hypothesis

```python
@dataclass
class Hypothesis:
    id: str                            # UUID
    session_id: str
    statement: str                     # e.g., "Candidate has strong Laravel skills"
    direction: str                     # "positive" | "negative" — is the statement affirming or doubting?
    confidence: float                  # 0.0-1.0 (0 = untested, 1 = certain)
    supporting_evidence: List[str]     # evidence IDs that support
    contradicting_evidence: List[str]  # evidence IDs that contradict
    status: str                        # "untested" | "testing" | "confirmed" | "refuted"
    created_at: datetime
    last_updated: datetime
```

### 6.4 EvidenceStore (persistent)

```python
@dataclass
class EvidenceStore:
    id: str                            # UUID
    session_id: str                    # FK to interview_sessions
    competency: str
    dimension: str
    score: float                       # 0.0-10.0
    confidence: float                  # 0.0-1.0
    evidence_text: str
    source_question: str
    question_number: int
    hypothesis_id: Optional[str]
    hypothesis_relevance: Optional[float]
    metadata: dict
    created_at: datetime
```

### 6.5 InterviewObjective

```python
@dataclass
class InterviewObjective:
    id: str
    session_id: str
    competency: str
    dimension: str
    hypothesis_id: str
    hypothesis_statement: str
    hypothesis_confidence: float       # confidence at time of objective creation
    status: str                        # "pending" | "probed" | "satisfied"
    evidence_ids: List[str]
    priority: int
    created_at: datetime
```

### 6.6 ConsistencyCheck

```python
@dataclass
class ConsistencyCheck:
    id: str
    session_id: str
    dimension: str
    answers_compared: dict             # {answer_1_id, answer_2_id}
    consistency_score: float           # 0.0-1.0
    contradictions: List[Dict]         # [{claim_a, claim_b, severity}]
    created_at: datetime
```

### 6.7 Observation

```python
@dataclass
class Observation:
    id: str
    session_id: str
    question_number: int
    type: str                          # "verbosity" | "hedging" | "certainty_shift" | "sentiment_shift"
    value: float                       # normalized 0.0-1.0
    evidence: str                      # what was observed
    pattern: Optional[str]             # trend across session
    risk_signal: Optional[Dict]        # {signal, severity} if applicable
    created_at: datetime
```

---

## 7. New DB Schemas

### 7.1 `evidence_store`

```sql
CREATE TABLE evidence_store (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    competency        VARCHAR(64) NOT NULL,
    dimension         VARCHAR(32) NOT NULL CHECK (dimension IN ('technical','communication','reasoning','behavioral','confidence','completeness')),
    score             REAL NOT NULL CHECK (score >= 0 AND score <= 10),
    confidence        REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    evidence_text     TEXT NOT NULL,
    source_question   TEXT NOT NULL,
    question_number   INTEGER NOT NULL,
    hypothesis_id     UUID,
    hypothesis_relevance REAL,
    metadata          JSONB DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_store_session ON evidence_store(session_id);
CREATE INDEX idx_evidence_store_competency ON evidence_store(session_id, competency);
CREATE INDEX idx_evidence_store_dimension ON evidence_store(session_id, dimension);
CREATE INDEX idx_evidence_store_hypothesis ON evidence_store(hypothesis_id);
```

### 7.2 `candidate_profiles` (extension of existing table)

```sql
-- Add JSONB column to existing candidate_profiles table
ALTER TABLE candidate_profiles ADD COLUMN IF NOT EXISTS profile_data JSONB DEFAULT '{}'::jsonb;

-- profile_data stores the full CandidateProfile struct as JSON
```

No new table needed. The existing `candidate_profiles` table gets one new JSONB column. This avoids schema bloat and keeps profile access fast.

### 7.3 `hypotheses`

```sql
CREATE TABLE hypotheses (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    statement         TEXT NOT NULL,
    direction         VARCHAR(16) NOT NULL CHECK (direction IN ('positive', 'negative')),
    confidence        REAL NOT NULL DEFAULT 0.0 CHECK (confidence >= 0 AND confidence <= 1),
    supporting_evidence UUID[] DEFAULT '{}',
    contradicting_evidence UUID[] DEFAULT '{}',
    status            VARCHAR(16) NOT NULL DEFAULT 'untested'
                      CHECK (status IN ('untested', 'testing', 'confirmed', 'refuted')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_hypotheses_session ON hypotheses(session_id);
CREATE INDEX idx_hypotheses_status ON hypotheses(session_id, status);
```

### 7.4 `interview_objectives`

```sql
CREATE TABLE interview_objectives (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id            UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    competency            VARCHAR(64) NOT NULL,
    dimension             VARCHAR(32) NOT NULL,
    hypothesis_id         UUID NOT NULL REFERENCES hypotheses(id),
    hypothesis_statement  TEXT NOT NULL,
    hypothesis_confidence REAL NOT NULL,
    status                VARCHAR(16) NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending', 'probed', 'satisfied')),
    evidence_ids          UUID[] DEFAULT '{}',
    priority              INTEGER NOT NULL DEFAULT 1,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interview_objectives_session ON interview_objectives(session_id);
CREATE INDEX idx_interview_objectives_status ON interview_objectives(session_id, status);
```

### 7.5 `consistency_checks`

```sql
CREATE TABLE consistency_checks (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    dimension         VARCHAR(32) NOT NULL,
    answers_compared  JSONB NOT NULL,
    consistency_score REAL NOT NULL CHECK (consistency_score >= 0 AND consistency_score <= 1),
    contradictions    JSONB DEFAULT '[]'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_consistency_checks_session ON consistency_checks(session_id);
```

### 7.6 `observations`

```sql
CREATE TABLE observations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    question_number   INTEGER NOT NULL,
    type              VARCHAR(32) NOT NULL,
    value             REAL NOT NULL CHECK (value >= 0 AND value <= 1),
    evidence          TEXT NOT NULL,
    pattern           VARCHAR(256),
    risk_signal       JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_observations_session ON observations(session_id);
CREATE INDEX idx_observations_type ON observations(session_id, type);
```

---

## 8. Nested LangGraph Subgraphs

### 8.1 Rationale

**One massive graph** is hard to debug, test, and maintain. **Three nested subgraphs** under an **Interview Supervisor** give:
- **Independent testability** — each subgraph can be invoked and tested with mock state
- **Clear boundaries** — question generation failures don't affect evaluation logic
- **Simpler routing** — each subgraph has a single entry/exit point
- **Performance isolation** — subgraphs can be cached, skipped, or retried independently

### 8.2 Subgraph Definitions

```
┌──────────────────────────────────────────────────────────────┐
│                   INTERVIEW SUPERVISOR                        │
│  (orchestrates lifecycle: profile → strategy → main loop)    │
│                                                              │
│  Entry points:                                               │
│  - start_interview                                           │
│  - process_answer                                            │
│  - next_question                                             │
│                                                              │
│  State: full InterviewState (shared across subgraphs)        │
└────────────────────────────────┬─────────────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ▼                                     ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│   QUESTION SUBGRAPH     │       │   EVALUATION SUBGRAPH   │
│                         │       │                         │
│  Question Planner       │       │  Unified Evaluator      │
│         │               │       │         │               │
│         ▼               │       │         ▼               │
│  Question Generator     │       │  Evidence Extractor     │
│         │               │       │         │               │
│         ▼               │       │         ▼               │
│       END               │       │       END               │
│  (returns question)     │       │  (returns evidence)     │
└─────────────────────────┘       └─────────────────────────┘
                                             │
                                             ▼
                                   ┌─────────────────────────┐
                                   │   REFLECTION SUBGRAPH    │
                                   │                          │
                                   │  Consistency Checker     │
                                   │         │               │
                                   │         ▼               │
                                   │  Observation Analyzer   │
                                   │         │               │
                                   │         ▼               │
                                   │  Reflection Engine      │
                                   │         │               │
                                   │         ▼               │
                                   │       END               │
                                   │  (returns next_action)  │
                                   └─────────────────────────┘
                                              │
                                     (action routed by supervisor)
```

### 8.3 Supervisor Flow

```
START → CandidateProfileLoader → CompanyKnowledgeLoader
     → InterviewStrategy (if cache invalid)
     → CompetencyPlanner (deterministic)
     → HypothesisManager (generate initial hypotheses)

LOOP:
    1. HypothesisManager.next_target() → most uncertain hypothesis
    2. Question Subgraph:
       - QuestionPlanner(most_uncertain_hypothesis, competency_gaps)
       - QuestionGenerator(question_objective, persona)
       → returns question_text
       → sends to candidate

    3. Candidate submits answer
    4. Evaluation Subgraph:
       - UnifiedEvaluator(question, answer) → 6-dimension scores + observations
       - EvidenceExtractor(evaluation) → structured evidence + competency_summary update
       → returns extracted_evidence

    5. HypothesisManager.update_hypotheses(evidence) → new confidences
    6. CandidateProfileLoader.update(evidence) → save back to DB

    7. Reflection Subgraph:
       - ConsistencyChecker(current_evidence, past_evidence) → contradictions
       - ObservationAnalyzer(observations) → trends + risk signals
       - ReflectionEngine(gaps, hypotheses, consistency, observations) → next_action
       → returns action

    8. Action Router:
       - "probe" → LOOP with same competency, depth+1
       - "change_competency" → LOOP with new competency target
       - "increase_difficulty" → LOOP with increased difficulty
       - "finish" → Synthesis → END
```

### 8.4 LangGraph Implementation Note

LangGraph supports `StateGraph` with `subgraph` nodes. Each subgraph is a compiled `StateGraph` with its own nodes and edges, registered as a single node in the parent graph:

```python
# Parent: Interview Supervisor
supervisor = StateGraph(InterviewState)
supervisor.add_node("question_subgraph", question_compiled_subgraph)
supervisor.add_node("evaluation_subgraph", evaluation_compiled_subgraph)
supervisor.add_node("reflection_subgraph", reflection_compiled_subgraph)

# Subgraph: Question
question_subgraph = StateGraph(QuestionState)
question_subgraph.add_node("planner", question_planner_node)
question_subgraph.add_node("generator", question_generation_node)
question_subgraph.add_edge("planner", "generator")
question_subgraph.add_edge("generator", END)
question_compiled_subgraph = question_subgraph.compile()
```

---

## 9. Unified Evaluator

### 9.1 Why Unified

| Approach | LLM Calls per Answer | Calls for 15 Questions | Cost | Quality |
|----------|---------------------|----------------------|------|---------|
| 6 parallel evaluators | 6 | 90 | 6x | Higher per-dimension detail |
| **Unified evaluator** (v4 default) | **1** | **15** | **1x** | Same JSON structure |
| Hybrid (enterprise) | 1 or 6 configurable | 15-90 | 1-6x | Configurable per style |

The unified evaluator produces identical JSON structure to 6 parallel calls — but with one prompt, one context window, one LLM call. The LLM handles all 6 dimensions internally. Quality is equivalent because:
- The prompt explicitly enumerates all 6 dimensions with criteria
- The output schema forces structured JSON per dimension
- The LLM naturally considers the whole answer before scoring each dimension

Enterprise/research modes that need maximum accuracy can switch to parallel via `evaluator_mode: "parallel"`.

### 9.2 Evaluator Dimensions

| # | Dimension | Criteria | Weight (Standard) |
|---|-----------|----------|------------------|
| 1 | **Technical** | Correctness, depth, accuracy, best practices | 0.30 |
| 2 | **Communication** | Clarity, structure, conciseness, vocabulary | 0.15 |
| 3 | **Reasoning** | Logic, structure, alternatives considered, depth of thought | 0.20 |
| 4 | **Behavioral** | STAR method, self-awareness, team orientation, ownership | 0.15 |
| 5 | **Confidence** | Certainty in answers, honesty about unknowns, pushback ability | 0.10 |
| 6 | **Completeness** | Did they fully answer? Coverage of sub-parts, thoroughness | 0.10 |

### 9.3 Composite Score

```python
composite_score = sum(
    evaluations[dim]["score"] * weights[dim]
    for dim in evaluations
)
```

Weights come from interview style config. FAANG style weights technical=0.4, reasoning=0.3; BEHAVIORAL style weights behavioral=0.4, communication=0.3.

---

## 10. Hypothesis Manager

### 10.1 Why Hypotheses

v3 asked: *"What skill do I need to test next?"*

v4 asks: *"What do I believe about this candidate, and which belief is most uncertain?"*

This is closer to how humans interview. Experienced interviewers form opinions early and spend the rest of the interview either confirming or refuting them.

### 10.2 Hypothesis Lifecycle

```
                   Untested (confidence = 0.0)
                        │
                        ▼  first evidence arrives
                   Testing (0.0 < confidence < 0.8)
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
        Confirmed            Refuted
     (confidence ≥ 0.8)    (confidence ≤ 0.2)
```

### 10.3 Initial Hypotheses

Generated at session start from:
1. **Resume keywords** → positive hypotheses ("Strong Laravel", "Experienced with Docker")
2. **Job requirements not in resume** → negative hypotheses ("Weak database", "No cloud experience")
3. **Candidate profile from past sessions** → positive/negative based on historic scores
4. **Defaults** → neutral hypotheses ("Average communication skills")

### 10.4 Update Rule

```python
def update(self, evidence_list):
    for evidence in evidence_list:
        for hypothesis in self.active_hypotheses:
            relevance = self._compute_relevance(hypothesis, evidence)
            if relevance < 0.3:
                continue
            delta = (evidence.score / 10.0) * relevance * self.learning_rate
            # Positive hypothesis: high score → confidence up
            # Negative hypothesis: low score → confidence up
            if hypothesis.direction == "positive":
                hypothesis.confidence += delta if evidence.score >= 5.0 else -delta
            else:
                hypothesis.confidence += delta if evidence.score < 5.0 else -delta
            hypothesis.confidence = max(0.0, min(1.0, hypothesis.confidence))
            hypothesis.last_updated = now()
            if delta > 0:
                hypothesis.supporting_evidence.append(evidence.id)
            else:
                hypothesis.contradicting_evidence.append(evidence.id)
        # Update status
        if hypothesis.confidence >= 0.8:
            hypothesis.status = "confirmed"
        elif hypothesis.confidence <= 0.2:
            hypothesis.status = "refuted"
        else:
            hypothesis.status = "testing"
```

### 10.5 Next Target Selection

```python
def next_target(self):
    # Most uncertain = closest to 0.5
    untested = [h for h in self.active_hypotheses if h.status == "untested"]
    if untested:
        return untested[0]  # test untested first
    # Among testing hypotheses, pick the one closest to 0.5
    testing = [h for h in self.active_hypotheses if h.status == "testing"]
    if testing:
        return min(testing, key=lambda h: abs(h.confidence - 0.5))
    # All confirmed or refuted — optional: deep probe on confirmed strengths
    confirmed = [h for h in self.active_hypotheses if h.status == "confirmed"]
    return max(confirmed, key=lambda h: h.confidence) if confirmed else None
```

---

## 11. Observation Layer

### 11.1 Extracted Signals

The Unified Evaluator extracts these from the answer text (no separate LLM call):

| Observation | Type | Range | What It Detects |
|-------------|------|-------|-----------------|
| Verbosity | `verbosity` | 0.0 (terse) – 1.0 (rambling) | Answer length vs complexity |
| Hedging | `hedging` | 0.0 (direct) – 1.0 (uncertain) | "I think", "maybe", "perhaps" frequency |
| Certainty shift | `certainty_shift` | -1.0 to +1.0 | Change from previous answer |
| Sentiment shift | `sentiment_shift` | categorical | "positive", "neutral", "defensive", "excited", "fatigued" |
| Response latency | `response_latency` | categorical | "quick", "medium", "hesitant", "very_hesitant" |

### 11.2 Aggregated Trends

The Observation Analyzer computes trends across the session:

```python
{
    "verbosity_trend": "increasing",     # candidate getting more verbose
    "hedging_trend": "stable",
    "certainty_trend": "improving",
    "emotional_state": "engaged",        # current state
    "notable_events": [
        {"question": 3, "event": "became defensive when pressed on SQL"},
        {"question": 7, "event": "showed excitement discussing system design"}
    ],
    "risk_signals": [
        {"signal": "defensive_response", "severity": "medium", "evidence": "...", "question": 3}
    ]
}
```

### 11.3 How Observations Affect the Loop

| Observation Signal | Reflection Engine Impact |
|-------------------|------------------------|
| Defensive pattern detected | Switch persona to "mentor", change competency to safe topic |
| Hedging increasing | Probe for confidence: ask "Are you sure?" follow-up |
| Verbosity increasing unexpectedly | Might indicate insecurity — probe deeper |
| Certainty improving | Positive signal — keep current trajectory |
| Sentiment shift to "excited" | Double down on this topic — candidate is in flow |

---

## 12. Prompt Strategy

### 12.1 New Prompt Files

| Prompt File | Used By | Variables | LLM? |
|-------------|---------|-----------|------|
| `prompts/interview/strategy_brain.md` | Strategy Brain | `{{job_role}}`, `{{interview_style}}`, `{{candidate_profile}}`, `{{competency_taxonomy}}`, `{{company_context}}` | Yes (once) |
| `prompts/interview/question_planner.md` | Question Planner | `{{target_hypothesis}}`, `{{competency_gaps}}`, `{{conversation_history}}`, `{{persona}}`, `{{phase}}` | Yes |
| `prompts/interview/question_generation.md` | Question Generator (main) | `{{question_objective}}`, `{{company_context}}`, `{{persona}}`, `{{candidate_profile}}` | Yes |
| `prompts/interview/adaptive_question.md` | Question Generator (probe) | `{{main_question}}`, `{{last_answer}}`, `{{probe_depth}}`, `{{hypothesis}}`, `{{persona}}` | Yes |
| `prompts/interview/reflection_engine.md` | Reflection Engine | `{{evidence_gaps}}`, `{{hypotheses}}`, `{{consistency_checks}}`, `{{observations}}`, `{{interview_style}}` | Yes |
| `prompts/interview/consistency_checker.md` | Consistency Checker | `{{current_answer}}`, `{{previous_answers}}`, `{{candidate_profile}}`, `{{conversation_history}}` | Yes |
| `prompts/interview/evidence_extractor.md` | Evidence Extractor | `{{question}}`, `{{answer}}`, `{{evaluation}}`, `{{competency_taxonomy}}` | Yes |
| `prompts/evaluation/unified_evaluator.md` | Unified Evaluator | `{{question}}`, `{{answer}}`, `{{difficulty}}`, `{{job_role}}`, `{{competency}}`, `{{persona}}` | Yes |

### 12.2 Existing Prompts (Reused)

| Prompt File | Status | Notes |
|-------------|--------|-------|
| `prompts/system/interviewer_system.md` | Kept | Base system prompt for interviewer |
| `prompts/system/evaluator_system.md` | Kept | Referenced by unified evaluator |
| `prompts/system/followup_system.md` | Kept | Referenced by adaptive question generation |
| `prompts/evaluation/scoring_rules.md` | Kept | Referenced by unified evaluator |
| `prompts/evaluation/synthesis.md` | Kept | Final report generation, unchanged |
| `prompts/interview/skill_tracker.md` | Kept | Internal skill extraction (used by evidence extractor) |
| `prompts/interview/phase_decision.md` | Kept | Phase transitions (used by strategy brain) |

### 12.3 Deprecated Prompts (No Longer Used in v4)

| Prompt File | Replaced By |
|-------------|-------------|
| `prompts/interview/interview_flow.md` | Strategy brain (cached) + reflection engine |
| `prompts/interview/inquisitor.md` | Reflection engine + hypothesis manager |
| `prompts/evaluation/answer_evaluation.md` | Unified evaluator |
| 6 parallel evaluator prompt files | Unified evaluator (single file) |

---

## 13. API Changes

### 13.1 New Endpoints (`app/api/interview_v4.py`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/interviews/v4/styles` | List available interview styles with persona and difficulty |
| `GET` | `/interviews/v4/competencies` | List all 21 competencies from taxonomy |
| `POST` | `/interviews/v4/start` | Start v4 interview (accepts `job_role`, `style_name`, candidate profile) |
| `POST` | `/interviews/v4/{session_id}/answer` | Submit answer for unified 6-dimension evaluation |
| `GET` | `/interviews/v4/{session_id}/state` | Get current session state (q#, evidence count, hypothesis summary) |
| `GET` | `/interviews/v4/{session_id}/report` | Get final report with hiring verdict, competency summary, hypothesis outcomes |

All v4 endpoints are rate-limited via `RateLimitMiddleware` (60 req/min per IP) and have input validation on all fields.

### 13.2 Modified Endpoints (`app/api/interview_agent.py`)

The existing v3 endpoints now detect `engine_version` on `InterviewSession` and route accordingly:

| Endpoint | Routing Logic |
|----------|---------------|
| `POST /interviews/{id}/questions/next` | Checks `session.engine_version`. If `"v4"`, seeds v4 state and runs v4 pipeline. Falls back to v3 on failure. |
| `POST /interviews/{id}/answers` | Checks `session.engine_version`. If `"v4"`, runs v4 evaluation + hypothesis update + reflection. Falls back to v3 on failure. |
| `GET /interviews/{id}/summary` | Checks `session.engine_version`. If `"v4"`, returns v4-specific data (competency coverage, hypothesis outcomes). Falls back to v3. |
| `GET /interviews/{id}/status` | Unchanged — v3 orchestrator |
| `GET /interviews/{id}/rag-status` | Unchanged — v3 orchestrator |

### 13.3 State Seeding Flow

v4 state is **seeded at session creation**, not at first `/questions/next` call:

1. **Practice flow** (`POST /candidates/practice/start`): `start_practice()` reads `CandidateProfile.profile_data`, picks interview style from `PracticeStartRequest.interview_style`, seeds `V4SessionStore` immediately
2. **Marketplace flow** (`POST /public/interviews/{token}/start`): `start_public_interview()` reads `PublicInterview.style_name` + matches candidate by email for `profile_data`, seeds `V4SessionStore` immediately
3. **Legacy flow** (`_seed_v4_state()` in `interview_agent.py`): only fires if state wasn't already seeded — hardcodes STANDARD + empty profile as fallback

### 13.4 Response Shapes

**`POST /interviews/v4/start`:**
```json
{
    "session_id": "uuid",
    "status": "in_progress",
    "question": {
        "text": "Tell me about your experience with...",
        "number": 1,
        "target_competency": "tech_core",
        "target_hypothesis": "Candidate has strong Python skills"
    },
    "hypothesis_target": {
        "statement": "Candidate has strong Python skills",
        "confidence": 0.0,
        "status": "untested"
    },
    "persona": "friendly",
    "difficulty": 1,
    "competencies": {
        "planned": 21,
        "next": "tech_core"
    }
}
```

**`POST /interviews/v4/{session_id}/answer`:**
```json
{
    "session_id": "uuid",
    "status": "in_progress",
    "evaluation": {
        "scores": {
            "technical": {"score": 8.5, "evidence": "Explained async/await correctly...", "strengths": ["Deep understanding"], "weaknesses": []},
            "communication": {"score": 7.0, "evidence": "...", "strengths": [], "weaknesses": []},
            "reasoning": {"score": 9.0, "evidence": "...", "strengths": [], "weaknesses": []},
            "behavioral": {"score": 6.5, "evidence": "...", "strengths": [], "weaknesses": []},
            "confidence": {"score": 8.0, "evidence": "...", "strengths": [], "weaknesses": []},
            "completeness": {"score": 7.5, "evidence": "...", "strengths": [], "weaknesses": []}
        },
        "composite": 7.85
    },
    "next_question": {
        "text": "Can you elaborate on...",
        "number": 2,
        "target_competency": "tech_db"
    },
    "evidence": {
        "total": 6,
        "competencies_covered": 3,
        "competency_progress": {"tech_core": {"evidence_count": 2, "average_score": 8.0, "gap": 0.0}}
    },
    "hypothesis_progress": {"total": 6, "statuses": {"testing": 3, "untested": 3}},
    "contradictions": 0,
    "hiring_recommendation": {}
}
```

**`GET /interviews/v4/{session_id}/state`:**
```json
{
    "session_id": "uuid",
    "question_number": 3,
    "persona": "friendly",
    "difficulty": 1,
    "evidence_count": 12,
    "competency_coverage": {"tech_core": 3, "tech_framework": 2},
    "hypothesis_summary": {"total": 6, "confirmed": 1, "refuted": 0, "testing": 2},
    "contradictions": 0,
    "hiring_recommendation": {},
    "current_question": "What's your experience with...",
    "evaluation_score": 7.85
}
```

**`GET /interviews/v4/{session_id}/report`:**
```json
{
    "status": "completed",
    "hiring_recommendation": {
        "verdict": "strong_hire",
        "confidence": 0.85,
        "composite_score": 8.2,
        "coverage_ratio": 0.9
    },
    "competency_summary": {
        "tech_core": {"average_score": 8.5, "evidence_count": 3, "gap": 0.0}
    },
    "evidence_collected": 24,
    "questions_asked": 10,
    "hypothesis_outcomes": {"confirmed": 4, "refuted": 1, "untested": 0}
}
```

### 13.5 Persistence Layer

v4 session state is managed by `V4SessionStore` (`app/services/v4_session_store.py`):

- **In-memory dict** for fast reads/writes — every `get()` / `set()` is a dict lookup (~1μs)
- **PostgreSQL-backed** via the `v4_session_state` table — sessions survive restarts and multi-instance deploys
- **File fallback**: if `DATABASE_URL` is not set, falls back to `data/v4_sessions.json` (local dev without Supabase)
- **Dirty tracking**: Only changed sessions (`_dirty` set) are written during `flush()` — incremental, not full-dump
- **Auto-eviction**: Stale sessions >24h old are removed from both DB and memory on startup and can be evicted manually
- **Flush on shutdown**: Lifespan hook (`get_v4_session_store().flush()`) persists dirty sessions to DB
- **Singleton**: `get_v4_session_store()` returns a single process-wide instance

The `v4_session_state` table (`session_id UUID PK → JSONB state → TIMESTAMPTZ updated_at`) replaces the JSON file byte-for-byte. The DB audit tables (`evidence_store`, `hypotheses`, etc.) remain separate for permanent records.

### 13.6 DB Schema Additions

| Migration | Table/Column | Purpose |
|-----------|-------------|---------|
| `f0a1b2c3d4e5` | `evidence_store` | Scored evidence items with confidence |
| `f0a1b2c3d4e5` | `hypotheses` | Hypothesis statements with Bayesian belief state |
| `f0a1b2c3d4e5` | `interview_objectives` | Per-question targeting metadata |
| `f0a1b2c3d4e5` | `consistency_checks` | Cross-answer contradiction detection |
| `f0a1b2c3d4e5` | `observations` | Behavioral signals (verbosity, hedging, etc.) |
| `f0a1b2c3d4e5` | `candidate_profiles.profile_data` | Structured candidate profile (JSONB) |
| `b2a1c3d4e5f6` | `interview_sessions.engine_version` | Routing flag (`"v3"` / `"v4"`) |
| `c3d4e5f6a7b8` | `public_interviews.style_name` | Interview style per marketplace listing |
| `c4d5e6f7a8b9` | `v4_session_state` | JSONB session state for DB-backed `V4SessionStore` |

---

## 14. Migration Plan — 6 Phases

### Phase 1: Foundation (Week 1)

DB tables + data models + state fields + repositories. No behavioral change to v3.

**Files to create/modify**:
- `app/models/db.py` — add `EvidenceStore`, `Hypothesis`, `InterviewObjective`, `ConsistencyCheck`, `Observation` ORM models; add `profile_data JSONB` to `CandidateProfile`
- `alembic/versions/0002_add_v4_tables.py` — migration for new tables + column
- `app/graph/interview_state.py` — add v4 state fields
- `app/repositories/evidence_repository.py` — CRUD + session/competency/dimension queries + competency_summary computation
- `app/repositories/hypothesis_repository.py` — CRUD + session queries
- `app/repositories/observation_repository.py` — CRUD + session/type queries
- `app/config/interview_styles.py` — all 13 style definitions
- `app/data/competency_taxonomy.py` — competency definitions + skill-to-competency mapping

**Verification**: `alembic upgrade head` succeeds. Repositories write/read. All v3 tests pass.

### Phase 2: Planning & Profile (Week 2)

Deterministic planner, cached strategy brain, hypothesis manager, candidate profile.

**Files to create/modify**:
- `app/agents/strategy_brain_node.py` + `prompts/interview/strategy_brain.md`
- `app/agents/competency_planner.py` — pure Python, no LLM
- `app/agents/hypothesis_manager.py` — Bayesian update logic
- `app/agents/candidate_profile_node.py` — load/update structured profile
- `app/agents/action_router.py` — routing logic

**Verification**: Unit tests for planner sorting, hypothesis update math, profile serialization. Strategy brain caches correctly.

### Phase 3: Evaluation (Week 3)

Unified evaluator + evidence extractor.

**Files to create/modify**:
- `app/agents/unified_evaluator_node.py` + `prompts/evaluation/unified_evaluator.md`
- `app/agents/evidence_extractor_node.py` + `prompts/interview/evidence_extractor.md`

**Verification**: Unified evaluator returns 6-dimension JSON from 1 LLM call. Evidence extractor writes to DB + updates competency_summary + pushes to hypothesis manager. Integration test with sample Q&A.

### Phase 4: Reflection Subgraph (Week 4)

Consistency checker, observation analyzer, reflection engine.

**Files to create/modify**:
- `app/agents/consistency_checker_node.py` + `prompts/interview/consistency_checker.md`
- `app/agents/observation_analyzer.py` — aggregation logic, no LLM
- `app/agents/reflection_engine.py` + `prompts/interview/reflection_engine.md`

**Verification**: Reflection engine correctly identifies probe vs change_competency vs finish. Consistency checker catches contradictions. Observations trend correctly across multiple answers.

### Phase 5: Nested Subgraphs & Supervisor (Week 5)

Wire all subgraphs under the Interview Supervisor.

**Files to create/modify**:
- `app/graph/question_subgraph.py` — compiled subgraph
- `app/graph/evaluation_subgraph.py` — compiled subgraph
- `app/graph/reflection_subgraph.py` — compiled subgraph
- `app/graph/interview_supervisor.py` — top-level orchestration graph
- `app/orchestrators/interview_orchestrator.py` — v4 evidence-driven flow
- v3 graphs kept as deprecated wrappers

**Verification**: Full interview cycle executes across all 3 subgraphs. Hypotheses update. Evidence accumulates. Reflection engine drives routing. Hiring recommendation produced.

### Phase 6: Frontend & API (Week 6)

New API endpoints, frontend evidence/hypothesis display, backward compatibility.

**Files to create/modify**:
- `app/api/interview_v4.py` — 6 dedicated v4 endpoints with input validation + rate limiting
- `app/api/interview_agent.py` — add v4 engine_version routing to existing endpoints
- `app/services/v4_session_store.py` — JSON file-backed persistence, singleton, auto-eviction
- `app/middleware/rate_limit.py` — sliding-window per-IP rate limiter for v4 endpoints
- `app/utils/input_sanitizer.py` — prompt injection detection and answer sanitization
- `frontend/src/services/interviewService.ts` — v4 API client
- `frontend/src/controllers/interviewController.ts` — v4 hypothesis-aware controller
- `frontend/src/state/interviewStore.tsx` — v4 state fields
- `frontend/src/components/EvidencePanel.tsx` — shows evidence with confidence scores
- `frontend/src/components/HypothesisPanel.tsx` — shows hypothesis tracker
- `frontend/src/components/CompetencyCoverage.tsx` — shows competency progress
- `frontend/src/components/ObservationPanel.tsx` — shows behavioral observations
- `frontend/interview-v4.html` — standalone SPA for v4 interview flow

**Verification**: Frontend renders all new panels. Both v3 and v4 endpoints work. No regressions.

### Backward Compatibility

- v3 endpoints remain at original paths
- v4 endpoints at `/interviews/v4/*`
- v3 `InterviewState` fields remain (v4 fields are additive)
- v3 graphs remain importable (deprecated wrappers)
- `interview_style` defaults to `STANDARD`, `persona` defaults to `friendly`, `evaluator_mode` defaults to `unified`

---

## 15. Directory Structure After v4

```
app/
├── agents/
│   ├── action_router.py                # (+) routing logic
│   ├── answer_evaluator_node.py        # (v3, kept)
│   ├── candidate_profile_node.py       # (+) structured profile
│   ├── company_context_node.py         # (v3, enhanced)
│   ├── competency_planner.py           # (+) deterministic
│   ├── consistency_checker_node.py     # (+)
│   ├── decision_node.py                # (v3, kept)
│   ├── evidence_extractor_node.py      # (+)
│   ├── hypothesis_manager.py           # (+) Bayesian belief tracker
│   ├── inquisitor_node.py              # (v3, kept)
│   ├── interview_flow_node.py          # (v3, kept)
│   ├── observation_analyzer.py         # (+) aggregation, no LLM
│   ├── phase_decision_node.py          # (v3, kept)
│   ├── question_generation_node.py     # (v3, adapted for persona + hypothesis)
│   ├── question_planner_node.py        # (+)
│   ├── reflection_engine.py            # (+) merged reflection + decision
│   ├── session_init_node.py            # (v3, unchanged)
│   ├── skill_tracker_node.py           # (v3, kept)
│   ├── strategy_brain_node.py          # (+) cached LLM
│   ├── synthesis_node.py               # (v3, unchanged)
│   └── unified_evaluator_node.py       # (+) replaces 6 parallel evaluators
│
├── config/
│   └── interview_styles.py             # (+) 13 style definitions
│
├── data/
│   └── competency_taxonomy.py          # (+) 20 competencies + mapping
│
├── graph/
│   ├── interview_state.py              # (v3, enhanced)
│   ├── interview_supervisor.py         # (+) top-level graph
│   ├── question_subgraph.py            # (+) nested
│   ├── evaluation_subgraph.py          # (+) nested
│   ├── reflection_subgraph.py          # (+) nested
│   ├── question_workflow.py            # (v3, kept)
│   └── evaluation_workflow.py          # (v3, kept)
│
├── orchestrators/
│   └── interview_orchestrator.py       # (v3, enhanced)
│
├── repositories/
│   ├── base_repository.py              # (v3, unchanged)
│   ├── evidence_repository.py          # (+)
│   ├── hypothesis_repository.py        # (+)
│   ├── observation_repository.py       # (+)
│   ├── evaluation_repository.py        # (v3, unchanged)
│   ├── message_repository.py           # (v3, unchanged)
│   └── session_repository.py           # (v3, unchanged)
│
├── models/
│   └── db.py                           # (v3, +5 new ORM models)
│
├── api/
│   ├── interview_agent.py              # (v3, +v4 engine_version routing)
│   └── interview_v4.py                 # (+) 6 dedicated v4 endpoints
│
├── services/
│   └── v4_session_store.py             # (+) JSON file-backed session persistence
│
├── utils/
│   └── input_sanitizer.py              # (+) prompt injection detection + sanitization
│
prompts/
├── evaluation/
│   ├── unified_evaluator.md            # (+) replaces 6 files
│   ├── scoring_rules.md                # (v3, unchanged)
│   └── synthesis.md                    # (v3, unchanged)
│
├── interview/
│   ├── adaptive_question.md            # (v3, updated)
│   ├── competency_planner.md           # (deprecated — now deterministic)
│   ├── consistency_checker.md          # (+)
│   ├── evidence_extractor.md           # (+)
│   ├── inquisitor.md                   # (v3, kept)
│   ├── interview_flow.md               # (v3, kept)
│   ├── phase_decision.md               # (v3, unchanged)
│   ├── question_generation.md          # (v3, adapted)
│   ├── question_planner.md             # (+)
│   ├── reflection_engine.md            # (+)
│   ├── skill_tracker.md                # (v3, unchanged)
│   └── strategy_brain.md               # (+)
│
├── system/
│   ├── evaluator_system.md             # (v3, updated)
│   ├── followup_system.md              # (v3, unchanged)
│   └── interviewer_system.md           # (v3, updated)
│
database/migrations/versions/
├── 5d045fd43882_v2_fresh_schema.py
├── cb0990d55c7d_*.py
├── a3c8b7d1e9f0_*.py
├── d4e5f6a7b8c9_add_verification_token.py    # (existing) verification tokens
├── e9f8d7c6b5a4_add_marketplace_fields.py   # (existing) marketplace fields
├── f0a1b2c3d4e5_add_v4_tables.py            # (+) 5 tables + profile_data
├── b2a1c3d4e5f6_add_engine_version.py       # (+) engine_version on interview_sessions
├── c3d4e5f6a7b8_add_style_name.py           # (+) style_name on public_interviews
└── c4d5e6f7a8b9_add_v4_session_state.py     # (+) v4_session_state table
```

---

## 16. Appendix: State Field Reference

### v3 Fields (Preserved, 47 fields)

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | str | UUID |
| `department_id` | int | For RAG namespace |
| `candidate_id` | str | Candidate identifier |
| `job_role` | str | e.g. "Software Engineer" |
| `flow_type` | str | "department", "skill", "adaptive" |
| `conversation_history` | List[Dict] | Full transcript |
| `current_phase` | str | Phase identifier |
| `phase_stage` | int | Progress within phase |
| `question_number` | int | Current question index |
| `total_questions` | int | Max questions |
| `current_question` | str | Text of current question |
| `difficulty_level` | int | 1-3 |
| `question_depth` | int | Probe depth on current topic |
| `follow_up_count` | int | Total follow-ups on this topic |
| `topic_saturated` | bool | Topic sufficiently explored |
| `probe_question` | str | Follow-up question text |
| `probe_angle` | str | Angle to probe |
| `inquisitor_action` | str | "probe" / "saturate" / "main" |
| `is_follow_up` | bool | Current submission is follow-up |
| `main_question` | str | Original main question |
| `probing_history` | List[Dict] | History of probes |
| `skills_tested` | List[str] | Skills assessed so far |
| `skills_weak` | List[str] | Skills with low scores |
| `skills_uncovered` | List[str] | Areas not yet probed |
| `coverage_map` | Dict[str, float] | Skill → score mapping |
| `department_context` | List[Dict] | RAG context |
| `department_requirements` | str | RAG context text |
| `rag_metadata` | Dict | RAG metadata |
| `candidate_answer` | str | Current answer text |
| `evaluation_score` | float | 0-10 (composite) |
| `technical_score` | float | Technical sub-score |
| `communication_score` | float | Communication sub-score |
| `strengths` | List[str] | Answer strengths |
| `weaknesses` | List[str] | Answer weaknesses |
| `feedback_detail` | str | Full evaluation text |
| `evaluation_metadata` | Dict | Evaluation extras |
| `evaluation_failed` | bool | Evaluation error |
| `next_action` | str | "probe" / "continue" / "finish" / … |
| `suggested_follow_up` | str | Follow-up suggestion |
| `next_phase` | Optional[str] | Target phase |
| `next_difficulty` | Optional[int] | Target difficulty |
| `start_time` | Optional[datetime] | Session start |
| `elapsed_time` | Optional[int] | Seconds elapsed |
| `is_complete` | bool | Session complete |
| `final_report` | Optional[Dict] | Holistic report |
| `nodes_executed` | List[str] | Audit trail |
| `speech_metrics` | Dict[str, float] | Voice mode metrics |

### v4 New Fields (22+ fields)

*The core 22 v4-specific fields. Additional derived fields (`max_questions`, `questions_asked`, `skip_evaluation`, `flow_type`, `candidate_id`, `next_competency`, `competency_plan`) are set by individual nodes during the pipeline.*

| Field | Type | Description | Populated By |
|-------|------|-------------|-------------|
| `evidence_store` | List[Dict] | Accumulated evidence items with confidence | Evidence Extractor |
| `candidate_profile` | Dict | Structured candidate profile (typed, not key-value) | Candidate Profile Loader |
| `hypotheses` | List[Dict] | Active hypotheses with confidences | Hypothesis Manager |
| `hypothesis_target` | Optional[Dict] | Most uncertain hypothesis selected for next question | Hypothesis Manager |
| `required_competencies` | List[Dict] | Competencies with gaps (sorted) | Competency Planner |
| `competency_summary` | Dict[str, Dict] | Per-competency aggregate stats | Evidence Extractor |
| `interview_style` | Dict | Applied style config (persona, evaluator_mode, weights) | Orchestrator (start) |
| `interview_strategy` | Optional[Dict] | Cached strategy from strategy brain | Strategy Brain |
| `strategy_cache_valid` | bool | Whether strategy cache is fresh | Strategy Brain |
| `question_objective` | Optional[Dict] | Target for current question (includes hypothesis) | Question Planner |
| `unified_evaluation` | Optional[Dict] | 6-dimension evaluation from single LLM call | Unified Evaluator |
| `evaluator_mode` | str | "unified" or "parallel" | Interview Style |
| `extracted_evidence` | List[Dict] | Structured evidence items from current answer | Evidence Extractor |
| `observations` | List[Dict] | Behavioral observations from current answer | Unified Evaluator |
| `observation_trends` | Dict | Aggregated observation signals | Observation Analyzer |
| `consistency_checks` | List[Dict] | Cross-answer comparison results | Consistency Checker |
| `contradictions` | List[Dict] | Detected contradictions | Consistency Checker |
| `reflection_action` | Optional[Dict] | Reflection engine output (action + reasoning) | Reflection Engine |
| `hiring_recommendation` | Optional[str] | "Strong Hire" / "Hire" / "Lean Hire" / "Lean No-Hire" / "No-Hire" / "Insufficient Evidence" | Reflection Engine |
| `evidence_sufficiency` | float | % of required evidence collected (0.0-1.0) | Reflection Engine |
| `persona` | str | Active persona for question generation | Interview Style |
| `company_competency_requirements` | List[Dict] | Company-specific expectations per competency | Company Knowledge |

---

*End of v4 Architecture Document*
