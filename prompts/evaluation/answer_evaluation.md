# Evaluate Candidate Answer

# Purpose
Evaluate a candidate's answer with detailed feedback and scores.

# Instructions
Evaluate the candidate's answer as if you're providing honest, constructive feedback to the candidate.

**Scoring Guide**:
- **9-10**: Excellent - Demonstrates mastery/understanding, provides specific examples/details, logical and coherent
- **7-8**: Good - Solid understanding, minor gaps in some areas, mostly coherent, some specific details
- **5-6**: Fair - Understanding exists but incomplete, lacks specific details, might be vague or generic
- **3-4**: Poor - Missing key points, inaccurate understanding, may not truly understand the topic
- **0-2**: Very Poor - Fundamental misunderstandings

**Evaluation Criteria**:

1. **Technical Knowledge** (0.0-10.0): Accuracy of technical understanding, coverage of relevant concepts, depth of knowledge
2. **Problem Solving** (0.0-10.0): Reasoning and logic, approach to problems, presence of structured analysis
3. **Communication** (0.0-10.0): Clarity of expression, completeness, coherence, organization of thoughts

**Feedback Requirements**:
- **Strengths**: 3-5 specific strengths (what they did well)
- **Weaknesses**: 3-5 specific areas for improvement (2-3 sentences each)
- **Feedback**: Comprehensive feedback combining all points (3-5 sentences)

**Style**:
- Constructive and honest (don't sugarcoat but be fair)
- Specific with concrete examples
- Actionable suggestions
- Professional but approachable

# Constraints
- All scores must be floats between 0.0 and 10.0 inclusive
- Round scores to 1 decimal place
- strengths and weaknesses must be arrays with 3-5 items each
- feedback is 3-5 sentences
- No markdown formatting in JSON values
- Don't invent factual information about the candidate

# Output Format
```json
{
  "score": 7.5,
  "technical_score": 8.0,
  "communication_score": 7.0,
  "strengths": [
    "Provides strong tech-stack examples",
    "Explains reasoning clearly",
    "References previous experience"
  ],
  "weaknesses": [
    "Could use more specific metrics",
    "Missing industry best practices",
    "Only covers surface level"
  ],
  "feedback": "Your answer demonstrates solid understanding of the concept..."
}
```

# Actual Data to Evaluate

- **Job Role**: {{job_role}}
- **Interview Phase**: {{phase}}
- **Difficulty Level**: {{difficulty_level}}
- **Question Asked**: {{question}}
- **Candidate Answer**: {{candidate_answer}}
- **Department Context**: {{department_context}}
