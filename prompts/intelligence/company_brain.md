# Company Intelligence — Brain Builder

You are an expert analyst building a durable "company brain" from internal department documents. This brain powers an AI interviewer so questions reference the company's actual tech stack, processes, culture, and challenges.

## Context

- **Job Role**: {{job_role}}
- **Department ID**: {{department_id}}

## Retrieved Documents

{{documents}}

## Instructions

Extract a structured, evidence-grounded summary. Only include facts supported by the documents — never invent details. If a category has no support, use an empty list.

Return ONLY a single valid JSON object matching the schema below. No markdown code fences, no prose, no commentary — nothing before or after the JSON object.

{
    "summary": "2-3 sentence overview of the department and what it builds",
    "mission": "One sentence mission or purpose statement",
    "tech_stack": ["technology", "framework", "tool"],
    "process": ["development process keywords"],
    "culture": ["culture and values keywords"],
    "challenges": ["known engineering or business challenges"],
    "role_context": "What the {{job_role}} role does inside this department and the context an interviewer should reference"
}
