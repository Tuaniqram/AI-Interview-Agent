# CLAUDE PROMPT CATALOG — AI Interview Agent

> Last updated: 2026-11-06
> All prompts live under `prompts/`.
> Prompt loading is handled by `app/services/prompt_loader.py`.

## 1. How Prompts Are Loaded

Primary API:

```python
from app.services.prompt_loader import load_prompt

text = load_prompt(
    "interview",
    "question_generation.md",
    job_role="Backend Developer",
    phase="technical",
)
```

Path-based API:

```python
from app.services.prompt_loader import get_prompt_loader

text = get_prompt_loader().load_by_path(
    "marketplace/job_description.md",
    org_name="Example Org",
    title="Backend Developer",
)
```

Behavior:
- Files are cached in memory.
- Rendered prompts are cached by a hash of path + variables.
- Placeholders may use either `{{variable}}` or `{variable}`.
- Double braces are preferred when both forms exist.
- Missing placeholders are left as-is; they do not raise.
- Prompts are plain markdown text sent to the LLM.

## 2. Prompt Status Legend

| Status | Meaning |
|---|---|
| `GENERIC` | Not scope-specific; likely usable after review |
| `NEEDS IT REVIEW` | Contains department/company wording that must become organization/IT wording |
| `NEEDS REWRITE` | Assumptions conflict with the IT-only schema |
| `RUNTIME` | Used directly in the live interview path |

All prompts are inherited from the pre-IT-only system. **None have been fully audited for IT-only wording.**

## 3. Brain Builder Prompts

| Prompt | Consumer | Purpose | Variables | Status |
|---|---|---|---|---|
| `brain_builder/company_brain.md` | Brain builder | Build organization/company context | none detected | NEEDS IT REVIEW |
| `brain_builder/core_reasoning_agent.md` | Core reasoning | Core reasoning instructions | none detected | GENERIC |
| `brain_builder/role_brain.md` | Role brain | Role-specific reasoning | none detected | NEEDS IT REVIEW |

## 4. Decision Prompts

| Prompt | Consumer | Purpose | Variables | Status |
|---|---|---|---|---|
| `decision/hiring_decision.md` | `app/agents/decision/hiring_decision.py` | Explain final hiring verdict | `competency_summary`, `coverage_ratio`, `decision_rationale`, `decision_score`, `decision_signals`, `evidence_summary`, `fit_assessment`, `holistic_score`, `job_role`, `strengths`, `verdict`, `weaknesses` | GENERIC |

## 5. Difficulty Prompts

| Prompt | Consumer | Purpose | Variables | Status |
|---|---|---|---|---|
| `difficulty_governor/difficulty_governor.md` | `app/agents/planning/difficulty_engine.py` | Adjust interview difficulty | `answer_complexity`, `confidence_delta`, `contradiction_count`, `current`, `last_answer`, `recent_average_score`, `score_summary`, `target_confidence`, `target_status` | GENERIC |

## 6. Evaluation Prompts

| Prompt | Consumer | Purpose | Variables | Status |
|---|---|---|---|---|
| `evaluation/evidence_reading.md` | `app/agents/evaluation/evidence_reading.py` | Extract evidence from transcript | `evidence_transcript`, `job_role` | GENERIC |
| `evaluation/synthesis.md` | `app/agents/evaluation/synthesis.py` | Synthesize final assessment | `avg_score`, `canonical_score`, `coverage_map`, `evidence_strengths`, `evidence_weaknesses`, `growth_trend`, `job_role`, `max_difficulty`, `score_timeline`, `skills_tested`, `skills_weak` | GENERIC |
| `evaluation/unified_evaluator.md` | `app/agents/evaluation/candidate_evaluator.py` | Score one answer | `answer`, `candidate_memory`, `competency`, `difficulty`, `domain_label`, `job_role`, `persona`, `primary_dimension`, `question`, `rubric` | RUNTIME |

## 7. Intelligence Prompts

| Prompt | Consumer | Purpose | Variables | Status |
|---|---|---|---|---|
| `intelligence/company_brain.md` | `app/intelligence/company_intelligence_builder.py` | Analyze organization documents | `department_id`, `documents`, `job_role` | NEEDS IT REVIEW |
| `intelligence/interview_blueprint.md` | `app/intelligence/interview_blueprint_builder.py` | Build interview plan | `competency_list`, `difficulty_max`, `difficulty_min`, `focus_areas`, `job_role`, `persona`, `style_name`, `tech_stack` | GENERIC |
| `intelligence/resume_analysis.md` | `app/intelligence/resume_analyzer.py` | Extract resume facts | `job_role`, `resume_text` | GENERIC |
| `intelligence/role_competency_profiler.md` | `app/intelligence/role_competency_profiler.py` | Map role to competencies | `department_name`, `description`, `existing_competencies`, `job_role`, `org_name`, `seniority`, `skills_required`, `tech_stack` | NEEDS IT REVIEW |

## 8. Interview Prompts

| Prompt | Consumer | Purpose | Variables | Status |
|---|---|---|---|---|
| `interview/question_generation.md` | `app/agents/generation/question_generator.py` | Generate first/next question | `approach`, `avoid_topics`, `candidate_memory`, `candidate_profile`, `claims_to_verify`, `company_context`, `competency_info`, `conversation_history`, `department_context`, `difficulty`, `difficulty_level`, `followup_number`, `hypothesis`, `interview_mode`, `job_role`, `last_question`, `last_rejected`, `persona`, `phase`, `question_number`, `strategy_guidance`, `target_competency`, `total_questions` | NEEDS IT REVIEW |
| `interview/strategy_brain.md` | `app/agents/planning/strategy_planner.py` | Plan interview strategy | `candidate_strengths`, `candidate_weaknesses`, `competency_list`, `difficulty_max`, `difficulty_min`, `job_role`, `max_questions`, `persona`, `style_name` | GENERIC |

## 9. Marketplace Prompts

| Prompt | Consumer | Purpose | Variables | Status |
|---|---|---|---|---|
| `marketplace/job_description.md` | `app/services/marketplace_generator.py` | Generate rich listing description | `dept_name`, `interview_mode`, `org_name`, `skills`, `title` | NEEDS IT REVIEW |

## 10. Prompt-to-Agent Map

| Agent / Service | Prompt |
|---|---|
| `app/agents/decision/hiring_decision.py` | `decision/hiring_decision.md` |
| `app/agents/evaluation/candidate_evaluator.py` | `evaluation/unified_evaluator.md` |
| `app/agents/evaluation/evidence_reading.py` | `evaluation/evidence_reading.md` |
| `app/agents/evaluation/synthesis.py` | `evaluation/synthesis.md` |
| `app/agents/generation/question_generator.py` | `interview/question_generation.md` |
| `app/agents/planning/difficulty_engine.py` | `difficulty_governor/difficulty_governor.md` |
| `app/agents/planning/strategy_planner.py` | `interview/strategy_brain.md` |
| `app/intelligence/company_intelligence_builder.py` | `intelligence/company_brain.md` |
| `app/intelligence/interview_blueprint_builder.py` | `intelligence/interview_blueprint.md` |
| `app/intelligence/resume_analyzer.py` | `intelligence/resume_analysis.md` |
| `app/intelligence/role_competency_profiler.py` | `intelligence/role_competency_profiler.md` |
| `app/services/marketplace_generator.py` | `marketplace/job_description.md` |

## 11. IT-Only Prompt Changes Required

### 11.1 Replace department language

| Current language | Replace with |
|---|---|
| department | organization or IT team context |
| department_id | org_id |
| department_context | organization_context |
| dept_name | org_name |
| department requirements | organization IT requirements |

### 11.2 Enforce IT roles

Every role-aware prompt must:
- Receive a role validated against `it_roles`.
- Reject or fall back when the role is not an IT role.
- Never ask marketing, finance, HR, sales, or supply-chain questions.

### 11.3 Enforce IT competencies

- Only use competencies where `scope = 'IT'`.
- Prefer `role_competencies` for weighting and required levels.
- Do not invent non-IT competencies.

### 11.4 Prompt safety

- Treat candidate answers and resumes as untrusted text.
- Do not let document content override system instructions.
- Validate LLM JSON against schemas before persistence.
- Keep prompt outputs bounded by `max_tokens`.
- Never put secrets or API keys in prompts.

## 12. Prompt Change Checklist for Claude

Before changing a prompt:

- [ ] Confirm the prompt is still used by a current agent/service.
- [ ] Confirm the variables match the caller.
- [ ] Remove department assumptions.
- [ ] Confirm the role is IT-only.
- [ ] Confirm competencies are IT-only.
- [ ] Check the output contract still parses.
- [ ] Run the relevant targeted agent test.
- [ ] Update this catalog if the prompt path or variables change.

## 13. Known Prompt Gaps

- `brain_builder/*` prompts are legacy and not fully audited.
- `intelligence/company_brain.md` still uses `department_id` and `documents` from the old department model.
- `intelligence/role_competency_profiler.md` still uses `department_name`.
- `interview/question_generation.md` still uses `department_context`.
- `marketplace/job_description.md` still uses `dept_name`.
- No prompt currently validates that the selected role exists in `it_roles`; validation is done outside the prompt.
- No automated prompt-injection tests exist.
