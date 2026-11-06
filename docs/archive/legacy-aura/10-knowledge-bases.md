# 10 — Knowledge bases

> Last updated: 2026-08-09 · Tag: [AURA-1.3][T4-calibration-ranking]

## Competency taxonomy (`app/data/competency_taxonomy.py`)

**65 canonical competencies across 12 categories**, each with
`evidence_dimensions` and `default_min_evidence`:

- **technical** (12): `tech_core`, `tech_framework`, `tech_system_design`,
  `tech_data`, `tech_db`, `tech_devops`, `tech_testing`, `tech_security`,
  plus T1 re-added `tech_event_driven`, `tech_deployment`, `tech_caching`,
  `tech_data_modeling`
- **behavioral** (5): `behav_teamwork`, `behav_leadership`, `behav_conflict`,
  `behav_communication`, `behav_adaptability`
- **cognitive** (4): `cog_problem_solving`, `cog_analytical`, `cog_creativity`,
  `cog_decision_making`
- **experience** (4): `exp_project_depth`, `exp_domain`, `exp_scaling`,
  `exp_best_practices`
- **8 job families** (5 each): `commerce` (`com_*`), `marketing` (`mkt_*`),
  `design` (`des_*`), `product` (`prd_*`), `hr` (`hr_*`), `finance` (`fin_*`),
  `operations` (`ops_*`), `customer_success` (`cs_*`)

Non-engineering competencies lead with the `domain` evidence dimension
(`DEFAULT_DIMENSIONS_BY_CATEGORY` in the resolver maps each family category to
`domain` + a secondary dimension). `SKILL_TO_COMPETENCY` maps skills (seo,
roadmap, churn, …) to competency ids; `map_skill_to_competency` defaults to
`tech_core` for unknown skills.

## Competency graph (`app/data/competency_graph.py`)

`COMPETENCY_CHILDREN` gives each competency its probeable sub-capabilities
(e.g. `tech_db` → indexing, query_optimization, sharding, data_modeling,
transactions, replication). `taxonomy_to_graph` projects the global graph onto a
session taxonomy (unknown AI-profiled ids degrade to stub nodes). Used by the
brain assembler and `missing_evidence_for`.

## Role brain (`app/brain/role_brain.py`)

Answers "what does this role actually require?" — deterministic, never generated
by the LLM:
- `_ROLE_CLASSES` (15): backend / frontend / fullstack / ml / data / devops /
  mobile / sales / marketing / design / product / hr / finance / operations /
  customer_success, each with keywords + mission; everything else → `general`.
- `classify_seniority`: staff/senior/mid/junior from title keywords.
- `_CANONICAL_IMPORTANCE` + `_ID_IMPORTANCE_BOOST` → `importance` 1..10 per comp.
- `default_probe_for`: "must prove" probe per competency (8 tech probes today).
- `build_role_brain` returns `{role, class, mission, seniority,
  critical_competencies, level_expectations, seniority_floor,
  emphasis_keywords, source}`.

## Company brain (`app/brain/company_brain.py`)

Company DNA: engineering philosophy, technical expectations, failure patterns,
culture signals, senior expectations. Grounded in department documents / tech
stack; never invented.

## Candidate brain / blueprint

- `candidate_brain`: resume summary, skills, strengths/weaknesses, inferred
  seniority, persona → initial hypotheses.
- `interview_blueprint`: role objectives, phases, hypothesis template, evidence
  requirements (built by `app/intelligence/interview_blueprint_builder.py`).

## Resolution chain (`app/data/competency_resolver.py:resolve_competencies`)

```
1. Org scorecard        (scorecard_templates.competencies)   — thin? skip to next
2. Department template  (interview_templates.competencies)   — thin? skip to next
3. AI role profiler     (suggest_competencies; LLM → validated → cached in-memory
                         + write-through to interview_templates.suggested_competencies)
4. Default taxonomy     (default_taxonomy())
```

- `is_thin_scorecard`: fewer than `MIN_SCORECARD_COMPETENCIES` (4) → triggers AI pass.
- `MAX_REQUIRED_COMPETENCIES = 6`: coverage targets a focused subset.
- `derive_required_competencies`: HIGH/MEDIUM priority subset capped at 6; a
  role-resolved taxonomy (≤6) is taken whole.
- `derive_domain_label`: `Technical Knowledge` if any technical category, else
  `Domain Knowledge`.

## AI role profiler (`app/intelligence/role_competency_profiler.py`)

- `build_role_context` serializes role facts (JSON-safe, cacheable).
- LLM pass validates entries against `_ID_RE`, `_CATEGORY_PREFIXES`
  (tech_/behav_/cog_/exp_/com_/mkt_/des_/prd_/hr_/fin_/ops_/cs_),
  `_CATEGORIES`, `_VALID_DIMENSIONS`.
- Deterministic fallback `_suggest_from_taxonomy` matches skills/keywords onto
  the taxonomy, then pads with family-aware anchors (`detect_family` resolves
  the role title/description onto one of the 8 families or `technical`).
- `use_llm=False` keeps resolution fully deterministic (tests, offline runs).

## Family-cohort comparability (T4)

Calibrated scores embed family-specific dimension weighting (T2 rubrics) and
difficulty-credit, so they are only directly comparable **within a family
cohort**. `detect_family` (used by the ranking endpoint and the drift report)
is the canonical role→family mapper; cross-family comparisons surface a
`comparable_note` rather than a silently misleading number, and the calibration
drift report buckets over/under-prediction by family so each cohort is
calibrated independently.
