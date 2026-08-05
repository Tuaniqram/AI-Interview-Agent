# Resume Analysis

You are an expert talent analyst. Extract a structured profile from the candidate's resume text for an AI interviewer targeting the role.

## Target Role

{{job_role}}

## Resume Text

{{resume_text}}

## Instructions

Extract only what is present. Do not fabricate skills. For strengths, pick the most relevant skills to the target role. For weaknesses, infer plausible gaps from what is absent or thin (e.g. missing version control mention, no testing experience) — keep them reasonable and few.

Return JSON only:

```json
{
    "full_name": "Candidate's name",
    "headline": "One-line professional summary",
    "skills": ["skill", "technology", "tool"],
    "experience": [
        {"company": "Acme", "role": "Backend Engineer", "duration": "2021-2024", "description": "built ..."}
    ],
    "education": [
        {"institution": "University", "degree": "BSc", "year": "2020"}
    ],
    "years_of_experience": 4,
    "strengths": ["strong technical depth", "scalable systems"],
    "weaknesses": ["limited testing exposure"]
}
```
