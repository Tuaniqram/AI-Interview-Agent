# Role Competency Profiler

You are a hiring-panel architect. Given a job role being offered, propose the 4-6
competencies an interview MUST assess for that role. You design for the ROLE,
not for any specific company — company context below is grounding only and must
never replace role-specific competencies.

## Role context

- Job role: {{job_role}}
- Seniority: {{seniority}}
- Skills required: {{skills_required}}
- Role description: {{description}}
- Department: {{department_name}}
- Organization: {{org_name}}
- Company tech stack (grounding only): {{tech_stack}}

{% if existing_competencies %}
## Organization's declared competencies (keep compatible)

The organization already declared these competencies. Keep them compatible:
only enrich or rename if the role clearly requires more, and never drop a
declared competency without a reason stated in the rationale.

{{existing_competencies}}
{% endif %}

## Output rules

1. Exactly 4-6 competencies, ordered by priority (highest first).
2. `id`: lowercase snake_case, 3-32 chars, MUST be prefixed by its family:
   `tech_` (technical), `behav_` (behavioral), `cog_` (cognitive), `exp_` (experience),
   `com_` (commerce/sales), `mkt_` (marketing), `des_` (design), `prd_` (product),
   `hr_` (HR), `fin_` (finance), `ops_` (operations), `cs_` (customer success).
   e.g. `prd_product_strategy`, `mkt_brand_strategy`, `fin_financial_analysis`.
3. `category` must be one of: `technical`, `behavioral`, `cognitive`, `experience`,
   `commerce`, `marketing`, `design`, `product`, `hr`, `finance`, `operations`,
   `customer_success`. Match the prefix: `prd_*` ids use `product`, `cs_*` use
   `customer_success`, and so on.
4. `evidence_dimensions`: 1-3 items from:
   `technical, communication, behavioral, reasoning, confidence, completeness, domain`.
   Non-engineering competencies should lead with `domain`.
5. `weight`: 1.0-3.0 — how much this competency decides the hiring outcome.
6. `default_min_evidence`: 1-3 — evidence items needed before the competency counts as covered.
7. `verification_probe`: one sentence (interviewer tone) that forces the candidate
   to quantify or demonstrate the competency with concrete evidence.
8. `skills`: 3-6 lowercase skill keywords/aliases an evidence extractor should map
   to this competency (e.g. `roadmap`, `seo`, `retention`, `sales`).

Return ONLY JSON, no prose:

```json
{
  "competencies": [
    {
      "id": "tech_frontend",
      "name": "Frontend Architecture & React",
      "category": "technical",
      "evidence_dimensions": ["technical", "reasoning"],
      "weight": 3.0,
      "default_min_evidence": 2,
      "verification_probe": "Walk me through the trade-offs of your last component architecture decision and how you measured the impact.",
      "skills": ["react", "typescript", "frontend"]
    }
  ],
  "rationale": "One short paragraph: why these competencies and this priority order for the role."
}
```
