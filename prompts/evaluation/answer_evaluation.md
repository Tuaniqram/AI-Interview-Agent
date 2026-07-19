# Evaluate Candidate Answer

# Purpose
Evaluate a candidate's answer with detailed feedback, scores, and suggested follow-up questions.

# Inputs
- job_role: Target job role (e.g., "Software Engineer")
- question: The question that was asked
- candidate_answer: The full candidate response (not just summary)
- phase: Current interview phase
- difficulty_level: Question difficulty (1, 2, or 3)

# Instructions
Evaluate the candidate's answer as if you're providing honest, constructive feedback to the candidate.

**Scoring Guide**:
- **2.0**: Excellent - Demonstrates mastery/understanding, provides specific examples/details, logical and coherent
- **1.5**: Good - Solid understanding, minor gaps in some areas, mostly coherent, some specific details
- **1.0**: Fair - Understanding exists but incomplete, lacks specific details, might be vague or generic
- **0.5**: Poor - Missing key points, inaccurate understanding, may not truly understand the topic
- **0.0**: Very Poor - Fundamental misunderstandings

**Evaluation Criteria** (each scored 0.0-2.0):

1. **Technical Knowledge**: Accuracy of technical understanding, coverage of relevant concepts, depth of knowledge
2. **Problem Solving**: Reasoning and logic, approach to problems, presence of structured analysis
3. **Communication**: Clarity of expression, completeness, coherence, organization of thoughts

**Feedback Requirements**:
- **Overall Assessment**: Brief overall judgment (1-2 sentences)
- **Strengths**: 3-5 specific strengths (what they did well)
- **Weaknesses**: 3-5 specific areas for improvement (2-3 sentences each)
- **Feedback Detail**: Comprehensive feedback combining all points (3-5 sentences)
- **Suggested Follow-up**: Natural follow-up question that digs deeper (1-2 sentences, no markdown)

**Style**:
- Constructive and honest (don't sugarcoat but be fair)
- Specific with concrete examples
- Actionable suggestions
- Professional but approachable
- No claims of knowing more than you do

# Constraints
- All scores must be floats between 0.0 and 2.0 inclusive
- Round scores to 1 decimal place
- strengths and weaknesses must be arrays with 3-5 items each
- suggested_follow_up is plain text (no markdown)
- feedback_detail is 3-5 sentences
- No markdown formatting in JSON values
- Don't invent factual information about the candidate

# Output Format
```json
{
  "overall_score": 1.5,
  "technical_score": 1.6,
  "communication_score": 1.4,
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
  "suggested_follow_up": "Can you give an example of how you handled \"X\" in a real project?",
  "feedback_detail": "Your answer demonstrates solid understanding of the concept. You provided good examples and explained your reasoning clearly. However, to get the same level of depth experts have, consider sharing specific metrics, including benchmarks, and mentioning how this approaches industry best practices."
}
```

# Examples

**Example 1 - Strong Answer**:
**Input**:
- job_role="Software Engineer"
- question="How do you optimize database queries that are running slowly?"
- answer="I always use EXPLAIN to see the execution plan first. Then I check if I'm hitting the right indexes. Usually I create composite indexes on the most common queries, or I denormalize tables for read-heavy workloads. I also cache frequently accessed data in Redis. For very complex queries, I break them down into smaller operations."
- difficulty_level=2

**Output**:
```json
{
  "overall_score": 1.8,
  "technical_score": 1.9,
  "communication_score": 1.6,
  "strengths": [
    "Familiar with EXPLAIN technique",
    "Covers indexing strategies",
    "Considers caching solutions",
    "Breaks complex problems down",
    "Practical, industry knowledge"
  ],
  "weaknesses": [
    "Mentioning Redis but not when it's appropriate vs database-level optimization",
    "Could mention query plan analysis tools"
  ],
  "suggested_follow_up": "Can you walk me through a specific slow query you optimized, the problem you found, and the metrics after improvement?",
  "feedback_detail": "Strong technical answer covering multiple optimization strategies. Good use of EXPLAIN and awareness of caching trade-offs. You demonstrate familiarity with standard optimization techniques. To further improve, consider discussing when to prioritize database-level vs caching optimization, and share a concrete example with before/after metrics to illustrate your approach."
}
```

**Example 2 - Weak Answer**:
**Input**:
- job_role="Software Engineer"
- question="Explain your experience with React"
- answer="I've used it a few times for small projects. It's okay, but sometimes I get confused with the hooks. Worked on maybe 2-3 things."
- difficulty_level=2

**Output**:
```json
{
  "overall_score": 0.8,
  "technical_score": 0.6,
  "communication_score": 1.0,
  "strengths": [
    "Tried React on real projects",
    "Honest about learning experience"
  ],
  "weaknesses": [
    "Only 2-3 projects total is quite limited experience",
    "Lacks specific examples or projects",
    "Generic answer without technical detail",
    "No mention of state management, hooks learning process",
    "Doesn't mention why React was chosen over alternatives"
  ],
  "suggested_follow_up": "Can you describe one specific component you built, the features it had, and what challenges you faced using React?",
  "feedback_detail": "This answer shows limited experience and doesn't demonstrate depth of knowledge. You mentioned using React on just 2-3 small projects, which is understandable for a learner, but it's crucial to have more hands-on practice and be able to discuss specific examples, challenges faced, and lessons learned to show genuine ability."
}
```

**Example 3 - Good Answer**:
**Input**:
- job_role="Product Manager"
- question="Tell me about a time you had to prioritize competing project requirements."
- answer="In my last role, we had 4 product requirements at once but only 3 engineers. I analyzed customer data and revenue impact, then had weekly sync meetings to adjust priorities based on changing needs. We successfully delivered 2 features that generated $30k revenue. Moving forward, I set up A/B testing protocols to measure impact more precisely."
- difficulty_level=1

**Output**:
```json
{
  "overall_score": 1.6,
  "technical_score": 1.2,
  "communication_score": 1.8,
  "strengths": [
    "Uses data to guide decisions",
    "Communicates clearly with metrics",
    "Meets deadlines despite resource constraints",
    "Ends with future improvements"
  ],
  "weaknesses": [
    "Could detail stakeholder communication approach",
    "Could mention trade-offs or compromises"
  ],
  "suggested_follow_up": "Can you describe which stakeholders you had to manage during the conflict and how you communicated those prioritization decisions?",
  "feedback_detail": "Strong answer demonstrating good prioritization skills. You used data-driven decision making, communicated effectively with metrics, and delivered results. You also showed forward-thinking by implementing A/B testing. To further strengthen, consider discussing how you communicated to potentially disappointed stakeholders and trade-offs you had to make."
}