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

All scores are on a **0.0 to 2.0 scale**, representing **0 to 10** when converted to 1.0-5.0 platform format.

**Score Ranges** (0.0-2.0):
- **2.0**: Excellent/Outstanding (70-100% - represents 7.0-10.0)
- **1.7-1.9**: Very Good (63-69% - represents 6.3-6.9)
- **1.4-1.6**: Good (50-62% - represents 5.0-6.2)
- **1.0-1.3**: Fair/Half (43-49% - represents 4.3-4.9)
- **0.5-0.9**: Poor (21-42% - represents 2.1-4.2)
- **0.1-0.4**: Very Poor (1-20% - represents 0.1-2.0)
- **0.0**: Fail (0% - represents 0.0)

**Conversion** (Platform count out of 50, converts to 1.0-5.0):
`score_0_10 = overall_score * 5.0`
`score_0_50 = score_0_10 * 5`

## Evaluation by Category

### 1. Technical Knowledge (0.0-2.0)

**What to Evaluate**:
- Accuracy of technical understanding
- Coverage of relevant concepts/terminology
- Depth of knowledge (surface vs deep)
- Recognition of trade-offs and limitations
- Industry best practices awareness
- Practical application vs theoretical knowledge

**Excellent (2.0)**:
- Demonstrates mastery/states with confidence about what they know
- Provides specific, concrete examples and cases
- Mentions industry standards, common patterns, and best practices
- Expresses awareness of limitations and edge cases
- Shows understanding of how concepts interconnect

**Good (1.5)**:
- Solid understanding of core concepts
- Mostly accurate, a few minor inaccuracies
- Provides some examples/details
- Understands fundamentals but lacks depth in some areas
- May not mention edge cases or limitations

**Fair (1.0)**:
- Understanding exists but is incomplete or generic
- Misses key concepts or details
- Lacks specific examples or case studies
- Superficial understanding (e.g., just name-dropping)
- Doesn't connect concepts

**Poor (0.5)**:
- Missing critical knowledge areas
- Fundamental misunderstandings
- Confuses concepts with similar ones
- Doesn't have practical experience to base understanding on

### 2. Problem Solving (0.0-2.0)

**What to Evaluate**:
- Reasoning and logical approach
- Structuring of the problem
- Breaking down complex problems
- Considering alternatives
- Testing/validating solutions
- Learning from experience

**Excellent (2.0)**:
- Clear, logical reasoning process
- Systematic approach (define, analyze, propose, validate)
- Considers multiple approaches and selects best one
- Mentions trade-offs and constraints
- References similar past problems and reusable patterns
- Validates solution through reasoning

**Good (1.5)**:
- Logical reasoning with some gaps
- Generally structured approach
- Considers reasonable alternatives
- Some consideration of trade-offs
- May skip validation step or do it minimally

**Fair (1.0)**:
- Reasoning is somewhat unclear or incomplete
- Solution may seem rushed or haphazard
- Limited consideration of different approaches
- Few or no trade-offs/alternatives discussed
- Might jump to answer without analysis

**Poor (0.5)**:
- Incoherent or illogical reasoning
- No clear approach or method
- Focuses on details without big picture
- Doesn't consider validation or testing
- Doesn't reference past experiences

### 3. Communication (0.0-2.0)

**What to Evaluate**:
- Clarity and organization of thoughts
- Completeness of answer (no major gaps)
- Coherence and flow
- Use of examples and evidence
- Answering the question asked
- Listening to follow-ups

**Excellent (2.0)**:
- Crystal clear communication
- Well-structured, easy to follow
- Completely answers the question
- Provides compelling examples/evidence
- Connects parts logically
- Engaging tone

**Good (1.5)**:
- Clear communication overall
- Mostly well-structured
- Generally answers the question
- Provides reasonable examples
- Some organizational issues

**Fair (1.0)**:
- Communication is vague or partially unclear
- Some organization but with gaps
- Misses parts of the question
- Limited or generic examples
- Important details omitted

**Poor (0.5)**:
- Communication is incoherent
- Poor organization that hinders understanding
- Doesn't answer the question adequately
- Lacks supporting examples
- Confusing or contradictory statements

## Difficulty Level Weighting

**Score Interpretation Adjustments**:

**Difficulty Level 1 (Easy, Foundational)**:
- Expect most experienced candidates to score 1.5-2.0
- Expect beginners to score 0.5-1.0
- Focus on basic understanding and recognition
- Lengthier answers expected (more time available)

**Difficulty Level 2 (Medium, Intermediate)**:
- Most relevant candidates should score 1.0-1.8
- Strong candidates score 1.8-2.0
- Weak candidates score 0.5-1.0
- Focus on application and workflow
- Brevity is acceptable as there's no time pressure

**Difficulty Level 3 (Hard, Advanced)**:
- Expect strong candidates to score 1.5-2.0
- Good candidates score 1.0-1.5
- Average candidates score 0.5-1.0
- Weak candidates score 0.0-0.5
- Focus on edge cases, optimizations, best practices
- Brevity is expected (advanced topics)

## Scoring Consistency

**For Pair Review**:
- Scores within ±0.3 of each other are consistent
- Scores outside this range need discussion
- Adjust scores if criteria have been interpreted differently

**For This Session**:
- Maintain same standards across all candidates
- Prompt difficulty adjustments should be reflected in scores
- Performance trends should be tracked over time

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

# Ensure within [0.0, 2.0]
final_score = max(0.0, min(2.0, final_score))
```

# Constraints
- Always round to 1 decimal place
- Never assign scores outside [0.0, 2.0]
- Weight percentages must sum to 100%
- Consider difficulty level when assessing consistency
- Base scores on what was actually said, not what you want to hear