# Scoring Rules

# Purpose
Define clear scoring criteria for evaluating candidate answers with guidance on score interpretation.

# Inputs
- job_role: Target job role
- question_type: Category of question (e.g., "Technical", "Behavioral", "Communication", "Problem Solving")
- candidate_answer: The full response
- phase: Current interview phase
- difficulty_level: Question difficulty level

# Instructions
Apply these scoring rules consistently to evaluate candidate answers.

## Scoring Scale

All scores are on a **0.0 to 10.0 scale**.

**Score Ranges** (0.0-10.0):
- **9.0-10.0**: Excellent/Outstanding - Mastery level
- **7.0-8.9**: Good - Solid understanding with minor gaps
- **5.0-6.9**: Fair - Understanding exists but incomplete
- **3.0-4.9**: Poor - Missing key points, significant gaps
- **0.1-2.9**: Very Poor - Fundamental misunderstandings
- **0.0**: Fail

## Evaluation by Category

### 1. Technical Knowledge (0.0-10.0)

**What to Evaluate**:
- Accuracy of technical understanding
- Coverage of relevant concepts/terminology
- Depth of knowledge (surface vs deep)
- Recognition of trade-offs and limitations
- Industry best practices awareness
- Practical application vs theoretical knowledge

**Excellent (9-10)**:
- Demonstrates mastery/states with confidence about what they know
- Provides specific, concrete examples and cases
- Mentions industry standards, common patterns, and best practices
- Expresses awareness of limitations and edge cases
- Shows understanding of how concepts interconnect

**Good (7-8)**:
- Solid understanding of core concepts
- Mostly accurate, a few minor inaccuracies
- Provides some examples/details
- Understands fundamentals but lacks depth in some areas
- May not mention edge cases or limitations

**Fair (5-6)**:
- Understanding exists but is incomplete or generic
- Misses key concepts or details
- Lacks specific examples or case studies
- Superficial understanding (e.g., just name-dropping)
- Doesn't connect concepts

**Poor (3-4)**:
- Missing critical knowledge areas
- Fundamental misunderstandings
- Confuses concepts with similar ones
- Doesn't have practical experience to base understanding on

### 2. Problem Solving (0.0-10.0)

**What to Evaluate**:
- Reasoning and logical approach
- Structuring of the problem
- Breaking down complex problems
- Considering alternatives
- Testing/validating solutions
- Learning from experience

**Excellent (9-10)**:
- Clear, logical reasoning process
- Systematic approach (define, analyze, propose, validate)
- Considers multiple approaches and selects best one
- Mentions trade-offs and constraints
- References similar past problems and reusable patterns
- Validates solution through reasoning

**Good (7-8)**:
- Logical reasoning with some gaps
- Generally structured approach
- Considers reasonable alternatives
- Some consideration of trade-offs
- May skip validation step or do it minimally

**Fair (5-6)**:
- Reasoning is somewhat unclear or incomplete
- Solution may seem rushed or haphazard
- Limited consideration of different approaches
- Few or no trade-offs/alternatives discussed
- Might jump to answer without analysis

**Poor (3-4)**:
- Incoherent or illogical reasoning
- No clear approach or method
- Focuses on details without big picture
- Doesn't consider validation or testing
- Doesn't reference past experiences

### 3. Communication (0.0-10.0)

**What to Evaluate**:
- Clarity and organization of thoughts
- Completeness of answer (no major gaps)
- Coherence and flow
- Use of examples and evidence
- Answering the question asked
- Listening to follow-ups

**Excellent (9-10)**:
- Crystal clear communication
- Well-structured, easy to follow
- Completely answers the question
- Provides compelling examples/evidence
- Connects parts logically
- Engaging tone

**Good (7-8)**:
- Clear communication overall
- Mostly well-structured
- Generally answers the question
- Provides reasonable examples
- Some organizational issues

**Fair (5-6)**:
- Communication is vague or partially unclear
- Some organization but with gaps
- Misses parts of the question
- Limited or generic examples
- Important details omitted

**Poor (3-4)**:
- Communication is incoherent
- Poor organization that hinders understanding
- Doesn't answer the question adequately
- Lacks supporting examples
- Confusing or contradictory statements

## Difficulty Level Weighting

**Difficulty Level 1 (Easy, Foundational)**:
- Expect most experienced candidates to score 7-10
- Expect beginners to score 3-5
- Focus on basic understanding and recognition

**Difficulty Level 2 (Medium, Intermediate)**:
- Most relevant candidates should score 5-9
- Strong candidates score 8-10
- Weak candidates score 3-5
- Focus on application and workflow

**Difficulty Level 3 (Hard, Advanced)**:
- Expect strong candidates to score 7-10
- Good candidates score 5-7
- Average candidates score 3-5
- Weak candidates score 0-3
- Focus on edge cases, optimizations, best practices

## Scoring Consistency

**Final Score Calculation**:
```python
# Weighted average
technical_weight = 0.4
problem_solving_weight = 0.3
communication_weight = 0.3

overall_score = (
    technical_score * technical_weight +
    problem_solving_score * problem_solving_weight +
    communication_score * communication_weight
)

# Round to 1 decimal
final_score = round(overall_score, 1)

# Ensure within [0.0, 10.0]
final_score = max(0.0, min(10.0, final_score))
```

# Constraints
- Always round to 1 decimal place
- Never assign scores outside [0.0, 10.0]
- Weight percentages must sum to 100%
- Consider difficulty level when assessing consistency
- Base scores on what was actually said, not what you want to hear

# Actual Data

- **Job Role**: {{job_role}}
- **Question Type**: {{question_type}}
- **Candidate Answer**: {{candidate_answer}}
- **Interview Phase**: {{phase}}
- **Difficulty Level**: {{difficulty_level}}
