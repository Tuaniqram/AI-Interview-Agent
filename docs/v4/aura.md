# AURA — Single-Mode Interview Engine

> **AURA** — Adaptive Unified Reasoning Assistant

A single intelligent conductor that replaces the 14-style interview picker. AURA builds its own plan per candidate and runs the whole interview as a natural conversation. No score cards mid-interview. No style selection. Just AURA.

**Design reference:** `frontend/public/aura-design.html` — J.A.R.V.I.S-style HUD interface (holographic core, animated rings, no human avatar).

---

## 1. Design Principles

### 1.1 One mode, one conductor
- No style picker. Every candidate gets AURA.
- AURA reads the role + profile + resume and builds its own plan (competency priorities, depth, pace) at runtime.
- Difficulty adapts on the fly: easy → harder; struggling → scaffolds.

### 1.2 Conversational, not quiz-like
- Each turn is a natural message: acknowledge → recall → probe/bridge.
- "2s to 50ms is a real win. Now let's stress it — what breaks at 100k concurrent writes?"
- Transitions are smooth. Never raw "Q4: What is React?"

### 1.3 Immersion-first
- No evaluation cards during the interview. Scores surface only in the final report.
- AURA runs silently in the background: evidence, hypotheses, contradictions — all invisible.
- Subtle status UI only: "AURA is thinking…", phase hint, never a number.

### 1.4 J.A.R.V.I.S aesthetic
- HUD interface: holographic energy core, concentric animated rings, grid overlay.
- No human avatar. The core pulses with conversation rhythm.
- Purple/blue accent palette. Dark background. Clean typography.

---

## 2. Persona

### AURA voice
Calm, precise, observant, warm-professional. Concise turns (1-3 sentences). Never evaluative mid-interview ("That's a nice pattern" ≠ "8/10"). Uses the candidate's name sparingly. Can gently challenge but never condescends.

### Identity rules
- Introduces itself once at start: "Hi, I'm AURA. I'll be conducting your interview today."
- Never reveals scores, evidence, hypotheses, or confidence levels.
- Never says "good answer" or "that's wrong" — stays neutral-observant.
- Acknowledges naturally: "Got it." / "Interesting." / "Let me dig into that."
- Bridges between topics: "Let's shift gears…" / "Now, about system design…"

---

## 3. Architecture

### 3.1 Reused v4 engine (no rework)
- `competency_planner_node` — adaptive planning
- `hypothesis_node` + `hypothesis_manager` — evidence-driven targeting
- `unified_evaluator_node` — silent evaluation
- `reflection_engine` — sufficiency, contradictions, finish decision
- `evidence_extractor_node` — evidence accumulation
- `synthesis_node` — final report
- `action_router` — routing logic
- Both API endpoints (`interview_v4.py` + `interview_agent.py`)

### 3.2 New backend pieces

#### A) Single style — `CONDUCTOR`
File: `app/config/interview_styles.py`
- Add `AURA` style: `persona: "conductor"`, `evaluator_mode: "unified"`, `difficulty_range: (1,4)`, no hard `max_questions` (governor-driven), balanced `evaluator_weights`.
- `list_styles()` returns only AURA. `get_style()` maps `"STANDARD"`/unknown → AURA.

#### B) Conductor persona prompt
File: `prompts/interview/conductor_persona.md`
- Identity, voice rules, conversation rules, silence-on-scores, adaptability rules.

#### C) Difficulty governor
File: `app/agents/difficulty_governor.py`
- Reads evaluation trend + hypothesis confidence → `difficulty_delta ∈ {-1,0,+1}`.
- Scaffolding rules: vague/low → "give me a concrete example"; strong → harder follow-up.
- One LLM call per turn + deterministic fallback.

#### D) Turn composer
File: `app/agents/question_generator_node.py`
- One LLM call producing `{acknowledgement, bridge, question}` from hypothesis target + prior evidence + last answer.
- `current_question` (evaluable) stays in `question_objective`.
- `conversation_turn` field carries the spoken message.
- Deterministic fallback preserved.

#### E) Response contract
Files: `app/api/interview_v4.py`, `app/api/interview_agent.py`
- `_build_*_response` add `conversation_turn` alongside `next_question`.
- No new routes needed.

### 3.3 Frontend

#### ConductorMode.tsx (new)
- Conversation-only UI: reuses `ConversationThread`/`InputBar` from `shared.tsx`.
- J.A.R.V.I.S HUD aesthetic: holographic core, animated rings, grid overlay.
- "AURA is thinking…" indicator (pulsing core animation).
- Corner phase hint ("Technical depth · 2 of 5").
- No mid-interview evaluation cards.
- Typing first; avatar/voice wrappers are later phases.

#### Style picker removal
- `pages/candidate/Practice.tsx` — remove `INTERVIEW_STYLES` selector.
- `routes/DepartmentDetail.tsx` — listing start uses AURA.
- `pages/org/Templates.tsx` — remove `interview_style` field.
- `pages/Landing.tsx` — 14-style grid → AURA hero card.

---

## 4. LLM Budget (10-turn session)

| Call | Count |
|------|-------|
| strategy_brain | 1 |
| difficulty governor | 1/turn |
| turn composer | 1/turn |
| unified evaluator | 1/turn |
| synthesis | 1 |
| **Total** | **~41** |

---

## 5. Implementation Phases

### Phase 1 — Design approval (current)
- `docs/v4/aura.md` (this file)
- `frontend/public/aura-design.html` (J.A.R.V.I.S HUD mockup)

### Phase 2 — Backend core
- `CONDUCTOR` style + `list_styles()` collapse
- `conductor_persona.md` prompt
- `difficulty_governor.py` node
- Turn composer in `question_generator_node.py`
- Response contract (`conversation_turn`)
- `reflection_engine` cap 14
- `strategy_brain` conductor handling
- Marketplace/candidates defaults → AURA
- Tests

### Phase 3 — Frontend immersion
- `ConductorMode.tsx` J.A.R.V.I.S HUD
- Remove style pickers
- Landing AURA hero card
- Store/routing updates
- Build verification

### Phase 4 — Voice/avatar (later)
- Voice wrapper around same conversation
- Holographic core visual (not human avatar)

---

## 6. Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| System name | AURA | Adaptive Unified Reasoning Assistant — calm, luminous, confident |
| Old styles | Hidden, kept in code | Tests/legacy routes still reference them |
| End condition | Evidence-driven | Ends when reflection_engine says sufficient, cap ~14 turns |
| Voice priority | Typing first | Ships faster; voice is a Phase 4 wrapper |
| Avatar style | J.A.R.V.I.S HUD | Holographic core + rings, no human face |
