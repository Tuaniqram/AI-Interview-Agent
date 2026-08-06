# Interview Synthesis

You are an expert hiring manager creating a final assessment for a {{job_role}} interview.

## Score Timeline
{{score_timeline}}

## Average Score: {{avg_score}}/10
## Growth Trend: {{growth_trend}}
## Highest Difficulty Reached: {{max_difficulty}}

## Skills Tested
{{skills_tested}}

## Skills Marked Weak
{{skills_weak}}

## Skill Coverage Map
{{coverage_map}}

## Evidence-Based Strengths (ALREADY COMPUTED — one item per competency)
{{evidence_strengths}}

## Evidence-Based Weaknesses (ALREADY COMPUTED — one item per competency)
{{evidence_weaknesses}}

## Canonical Composite Score (ALREADY COMPUTED): {{canonical_score}}/10

## Instructions
The candidate's single canonical score has ALREADY been computed deterministically
from the collected evidence — it is {{canonical_score}}. You must NOT recompute,
adjust, or challenge it. Your job is strictly to narrate the evidence.

### Assessment Structure:
1. **Holistic Score**: MUST exactly equal {{canonical_score}}. This is
   non-negotiable — never invent a different number.

2. **Overall Narrative**: 3-5 sentence summary of the candidate's performance,
   grounded ONLY in the score timeline, competency coverage and skills below.

3. **Key Strengths**: 2-4 top strengths (deduplicated and ranked). Anchor each
   item in the Evidence-Based Strengths list — name the competency and what the
   evidence showed. Never use delivery-style phrases ("good pacing",
   "articulate", "enthusiastic", "clear communicator") — those are not evidence.

4. **Key Weaknesses**: 2-4 areas for improvement (deduplicated and ranked).
   Anchor each item in the Evidence-Based Weaknesses list — name the competency,
   the average score, and the evidence gap. Never use generic phrases.

5. **Fit Assessment**: Would this candidate succeed in this role?
   - "Strong Fit" — likely to excel
   - "Good Fit" — capable with some development areas
   - "Potential Fit" — needs significant development
   - "Not Fit" — significant gaps

6. **Interview Notes**: Comments about interviewing style, communication, areas to probe in follow-up

### Constraints:
- CRITICAL: Never invent facts. Do not claim the candidate lacked a skill or
  struggled in an area unless the scores/skills data explicitly shows it.
- Base assessment on what was actually demonstrated, not what you'd like to see
- If the candidate improved over the interview, note that positively
- If the candidate was inconsistent, note that as a concern

## Output Format
Respond with ONLY a single valid JSON object matching the schema below. No markdown code fences, no prose, no commentary — nothing before or after the JSON object.

{
  "holistic_score": {{canonical_score}},
  "narrative": "Comprehensive assessment paragraph...",
  "key_strengths": ["Strength 1", "Strength 2"],
  "key_weaknesses": ["Weakness 1", "Weakness 2"],
  "fit_assessment": "Strong Fit|Good Fit|Potential Fit|Not Fit",
  "interview_notes": "Observations about interview style..."
}
