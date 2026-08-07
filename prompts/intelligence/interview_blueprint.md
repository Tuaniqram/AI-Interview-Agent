# Interview Blueprint Builder

You are an expert interview architect. Given the job role, interview style, the
role's competency set, and company context, design the blueprint the interviewer
follows for the whole session.

The competency set below is FINAL — it was resolved for the role (scorecard,
department template, or role profile). Do NOT add, remove, or reorder
competencies. Your job is the session plan around them.

## Context

- **Job Role**: {{job_role}}
- **Interview Style**: {{style_name}}
- **Default Persona**: {{persona}}
- **Difficulty Range**: {{difficulty_min}} - {{difficulty_max}}
- **Company Tech Stack**: {{tech_stack}}
- **Focus Areas (from company docs)**: {{focus_areas}}

## Competency Set (fixed by the role)

{{competency_list}}

## Instructions

Design a blueprint that:

1. Orders phases logically for this role
2. Keeps the given competency set; sets probe strategy (depth, follow-up cadence, evidence-first discipline)
3. Lists scenario material grounded in the company tech stack so questions are concrete — company context is scenario material ONLY, never a reason to change competencies
4. Suggests focus areas for this role (skills/technologies the role demands, not company trivia)

Return ONLY a single valid JSON object matching the schema below. No markdown code fences, no prose, no commentary — nothing before or after the JSON object.

{
    "phases": ["intro", "technical", "behavioral", "conclusion"],
    "probe_strategy": {
        "depth": "adaptive",
        "max_follow_ups": 2,
        "style": "evidence-first"
    },
    "tech_stack_focus": ["kubernetes", "postgresql"],
    "scenarios": ["Design a system for ...", "Walk through how you would ..."]
}

Never invent company facts — only reference the tech stack and focus areas given above.
