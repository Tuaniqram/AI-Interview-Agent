# 06 — Prompt inventory

> Last updated: 2026-08-09 · Tag: [AURA-1.6][evidence-reading]
> Loader: `app/services/prompt_loader.py` — reads `prompts/<category>/<file>`,
> renders `{{var}}` substitutions, caches per file.

## brain_builder (constitution + builders)

| File | Purpose | Injected variables | Loaded by |
|---|---|---|---|
| `core_reasoning_agent.md` | **The constitution** of the deterministic brain layers — rules for evidence levels, actions (`explore/verify/challenge/contradict/deepen/conclude`), difficulty, evidence graph | — | reference/design |
| `role_brain.md` | "What does this role actually require?" — mission + critical competencies with importance + probes. Rules: never generate competencies; resolved taxonomy is authoritative | role, skills, description, tech stack | `role_brain` build |
| `company_brain.md` | "What kind of engineer succeeds here?" — philosophy, technical expectations, failure patterns, senior expectations. Rules: derive from docs, never invent | department documents, tech stack | `company_intelligence_builder` |

## intelligence (session bundles)

| File | Purpose | Injected variables | Loaded by |
|---|---|---|---|
| `role_competency_profiler.md` | Propose competencies for a role (LLM pass of the profiler) | `job_role`, `seniority`, `skills_required`, `description`, `department_name`, `org_name`, `tech_stack`, `existing_competencies` | `suggest_competencies` (role_competency_profiler.py:245) |
| `resume_analysis.md` | Resume → candidate profile | resume text, role | resume analyzer |
| `interview_blueprint.md` | Role plan: objectives, phases, hypothesis template, evidence requirements | role, scorecard, candidate | `interview_blueprint_builder` |
| `company_brain.md` | Company brain builder (intelligence variant) | docs, tech stack | company builder |

## interview (conversation)

| File | Purpose | Injected variables | Loaded by |
|---|---|---|---|
| `question_generation.md` | **The conductor.** Generate ONE open-ended conversational question targeted at a hypothesis/competency. Modes EXPLORER/PROBER/CHALLENGER/VERIFIER/CLOSER, claim verification, candidate memory, duplicate avoidance, difficulty levels 1-5, voice rules (never reveal scoring) | `job_role`, `target_competency`, `phase`, `difficulty`, `difficulty_level`, `persona`, `hypothesis`, `competency_info`, `approach`, `followup_number`, `department_context`, `company_context`, `candidate_profile`, `question_number`, `total_questions`, `interview_mode`, `claims_to_verify`, `avoid_topics`, `last_question`, `last_rejected`, `conversation_history` | `question_generator_node` |
| `strategy_brain.md` | Design interview strategy: phase order, competency priority, difficulty range, persona, strategic intent, early-termination threshold | `job_role`, `style_name`, `persona`, `max_questions`, `difficulty_min/max`, `candidate_strengths/weaknesses`, `competency_list` | `strategy_brain_node` |

## evaluation

| File | Purpose | Injected variables | Loaded by |
|---|---|---|---|
| `unified_evaluator.md` | Score one answer across the family's **active dimensions** (tech: `technical` primary; non-tech families: `domain` primary, `technical` dropped) 0-10 with evidence, confidence, strengths/weaknesses + behavioral observations (verbosity, hedging, certainty_shift, sentiment_shift, latency, notable_patterns). Output: single JSON object. **T2**: rendered with the family rubric block and family-resolved labels | `question`, `answer`, `job_role`, `difficulty`, `persona`, `competency`, `domain_label`, `rubric`, `primary_dimension`, `candidate_memory` | `unified_evaluator_node` (candidate_evaluator.py:40) — `rubric`/`primary_dimension` sourced from `app/data/rubrics.py` (`render_rubric` :358, `active_dimensions` :313) |
| `synthesis.md` | Final assessment narration. Canonical score is already computed deterministically — the LLM only narrates evidence | `job_role`, `score_timeline`, `avg_score`, `growth_trend`, `max_difficulty`, `skills_tested`, `skills_weak`, `coverage_map`, `evidence_strengths`, `evidence_weaknesses`, `canonical_score` | synthesis node |
| `evidence_reading.md` | **Read** the raw answers semantically: classify each answer's claims (`proven`/`demonstrated`/`mentioned`) with `verifiable`/`specificity`/`ownership`, surface off-rubric red flags / hidden strengths and cross-answer risks. Must NOT score or set a verdict — the deterministic layers apply the downgrade-only rule | `job_role`, `evidence_transcript` | `evidence_reading_node` (evidence_reading.py) |

## difficulty_governor

| File | Purpose | Injected variables | Loaded by |
|---|---|---|---|
| `difficulty_governor.md` | Decide next-question difficulty delta (-1/0/+1) with hard binding rules (avg>8.3 → +1; avg>=7.0 → never -1; avg<7.0 → -1) and a `scaffold` instruction | `current`, `score_summary`, `recent_average_score`, `target_confidence`, `target_status`, `confidence_delta`, `answer_complexity`, `contradiction_count`, `last_answer` | `_govern_with_llm` (difficulty_engine.py:309) |

## decision

| File | Purpose | Injected variables | Loaded by |
|---|---|---|---|
| `hiring_decision.md` | Explain the already-computed deterministic decision in plain language. Must NOT change the verdict | `job_role`, `verdict`, `decision_score`, `decision_rationale`, `decision_signals`, `holistic_score`, `coverage_ratio`, `evidence_summary`, `fit_assessment`, `strengths`, `weaknesses`, `competency_summary` | hiring-decision node |

## marketplace

| File | Purpose | Injected variables | Loaded by |
|---|---|---|---|
| `job_description.md` | Enrich a listing's rich description | listing fields | `marketplace_generator` (listing creation only) |
