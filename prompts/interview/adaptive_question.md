# Generate Adaptive Follow-up Question

# Purpose
Generate an adaptive follow-up question based on the candidate's previous answer and interview performance.

# Instructions
Generate ONE follow-up question based on the candidate's answer:

1. **If answer was brief or incomplete**:
   - Ask for more details or specific examples
   - Probe deeper into what they mentioned

2. **If answer was strong**:
   - Test deeper understanding
   - Ask about edge cases or trade-offs

3. **If answer was weak**:
   - Simplify and clarify
   - Ask about fundamentals

**Adaptation Based on Performance**:
- **Score > 7** (Good): Dig deeper, ask practical application, test understanding
- **Score 5-7** (Fair): Clarify, ask about gaps, simplify if confusion exists
- **Score < 5** (Poor): Redirect to simpler version, ask foundational understanding

**Style Requirements**:
- Natural, conversational
- 1-2 sentences
- Open-ended
- Connect to candidate's specific answer
- No repetition of original question

# Constraints
- Connect to the company context — the candidate is applying to work in this specific industry, so questions must reference company domain details
- Generate exactly ONE question
- Don't ask questions already asked
- Don't invalidate the candidate's answer
- Stay on the same topic/subject
- Don't make question longer than 2 sentences

# Output Format
Return ONLY the follow-up question text, prefixed with "Question: ". No JSON, no explanation.

Example:
Question: Can you describe a specific project where you used that approach, and what challenges you encountered?

# Actual Data

- **Job Role**: {{job_role}}
- **Interview Phase**: {{phase}}
- **Previous Question**: {{previous_question}}
- **Candidate Answer**: {{candidate_answer}}
- **Difficulty Level**: {{difficulty_level}}
- **Previous Scores**: {{previous_scores}}
- **Company Context**: {{company_context}}
