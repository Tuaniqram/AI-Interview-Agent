# Holistic Interview Synthesis

# Purpose
Generate a holistic final assessment that goes beyond score averaging. Considers growth trajectory, consistency, difficulty adaptation, and skill coverage to produce a narrative evaluation.

# Inputs
- job_role: The role being interviewed for
- score_timeline: Chronological scores with phase labels
- average_score: Arithmetic mean of all scores
- growth_trend: "improving", "declining", or "stable"
- max_difficulty: Highest difficulty level reached (1-3)
- skills_tested: All skills assessed during the interview
- skills_weak: Skills with low scores (< 5.0)
- coverage_map: Skill name to score mapping
- probing_depth: How many follow-ups were needed per topic
- conversation_length: Total messages exchanged

# Instructions
Analyze the candidate's entire interview performance holistically.

## Key Dimensions:
1. **Consistency**: Did scores vary widely or stay stable across phases?
2. **Growth**: Did the candidate improve with each question or decline?
3. **Depth**: Could the candidate handle probing follow-ups? Did they elaborate or struggle?
4. **Difficulty Ceiling**: At what difficulty level did they peak?
5. **Skill Coverage**: Which key skills were demonstrated vs. missing?
6. **Communication**: How well did they articulate their thoughts?

## Scoring Guidelines:
- **9-10**: Exceptional — consistent mastery, handled deep probes, high difficulty
- **7-8**: Strong — solid across phases, some depth, probes handled well
- **5-6**: Adequate — met requirements, but limited depth or consistency
- **3-4**: Below expectations — significant gaps, struggled with probes
- **0-2**: Poor — fundamental misunderstandings

## Fit Assessment:
- **Strong Fit**: Exceeds requirements, would excel in the role
- **Good Fit**: Meets requirements, minor development areas
- **Potential Fit**: Shows promise but needs significant development
- **Not Fit**: Significant gaps relative to requirements

# Constraints
- Be honest — don't inflate scores to be "nice"
- Base assessment on demonstrated evidence, not assumptions
- If candidate had probe follow-ups, assess how they handled being pressed
- Note if they improved after probes (good sign) or got defensive/stuck (bad sign)
- Don't compare candidates to each other — assess against the role requirements

# Output Format
```json
{
  "holistic_score": 7.5,
  "narrative": "3-5 sentence holistic assessment...",
  "key_strengths": ["Strength 1", "Strength 2", "Strength 3"],
  "key_weaknesses": ["Weakness 1", "Weakness 2"],
  "fit_assessment": "Strong Fit|Good Fit|Potential Fit|Not Fit",
  "interview_notes": "Additional observations..."
}
```

# Actual Data

- **Job Role**: {{job_role}}
- **Score Timeline**: {{score_timeline}}
- **Average Score**: {{average_score}}
- **Growth Trend**: {{growth_trend}}
- **Max Difficulty Reached**: {{max_difficulty}}
- **Skills Tested**: {{skills_tested}}
- **Skills Weak**: {{skills_weak}}
- **Coverage Map**: {{coverage_map}}
- **Probing Depth**: {{probing_depth}}
