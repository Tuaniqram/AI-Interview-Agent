# Generate Adaptive Question

# Purpose
Generate an adaptive follow-up or modification question based on candidate's previous answer and interview performance.

# Inputs
- job_role: Target job role (e.g., "Software Engineer")
- phase: Current interview phase
- previous_question: The question just asked
- candidate_answer: The candidate's full response
- difficulty_level: Current difficulty level
- previous_scores: List of previous scores in this interview (for adaptation)

# Instructions
Generate ONE follow-up question or modify the current question if:

1. **Generate follow-up if**:
   - Candidate's answer was brief or incomplete
   - Candidate seemed unsure or defensive
   - Answer covered basics but didn't show depth
   - Answer lacked specific examples or details

2. **Modify question if**:
   - Candidate didn't understand the original question
   - Question seemed too vague or unclear
   - Need to test the same concept at a different difficulty level

**Adaptation Based on Performance**:
- **Score > 1.5** (Good): Dig deeper, ask practical application, test understanding
- **Score 1.0-1.5** (Fair): Clarify, ask about gaps, simplify if confusion exists
- **Score < 1.0** (Poor): Redirect to simpler version, ask foundational understanding

**Style Requirements**:
- Natural, conversational
- 1-2 sentences
- Open-ended
- Connect to candidate's specific answer
- No repetition of original question

# Constraints
- Generate exactly ONE question
- Don't ask questions already asked
- Don't invalidate the candidate's answer
- Stay on the same topic/subject
- Don't make question longer than 2 sentences

# Output Format
```json
{
  "question": "The follow-up question text",
  "adaptation_type": "followup" or "modification",
  "reason": "Brief explanation of why this question (optional, for internal tracking)"
}
```

# Examples

**Example 1 - Follow-up on weak answer**:
**Input**:
- question: "Explain your experience with React"
- answer: "I've used it a few times"
- difficulty_level: 2

**Output**:
```json
{
  "question": "Can you describe a specific project where you used React, and what challenges you encountered?",
  "adaptation_type": "followup",
  "reason": "Answer was too brief, need example"
}
```

**Example 2 - Follow-up on strong answer**:
**Input**:
- question: "Walk me through your database design process"
- answer: "I always normalize first, consider indexing, and write clean queries. I've used Postgres and Mongo extensively."
- difficulty_level: 3

**Output**:
```json
{
  "question": "How do you go about designing indexes in complex tables? I'm curious about your approach for optimizing queries.",
  "adaptation_type": "followup",
  "reason": "Good answer, testing deeper technical understanding"
}
```

**Example 3 - Modification (different difficulty)**:
**Input**:
- question: "How would you optimize a slow PostgreSQL query to handle millions of rows?"
- answer: "Uhhh I think I might use Docker? Maybe?"
- difficulty_level: 3

**Output**:
```json
{
  "question": "What SQL commands have you used to improve query performance on smaller datasets?",
  "adaptation_type": "modification",
  "reason": "Candidate clearly struggles with advanced concepts, simplify to test fundamentals"
}