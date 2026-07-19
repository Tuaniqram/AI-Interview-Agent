# Manage Interview Flow

# Purpose
Determine the next phase, question count, and difficulty level for the interview based on current state and performance tracking.

# Inputs
- job_role: Target job role (e.g., "Software Engineer")
- current_phase: Current phase (e.g., "intro", "experience", "technical", "behavioral", "conclusion")
- current_question_number: Current question number (0-indexed)
- total_questions_in_phase: Questions allocated to this phase
- overall_score: Average score across questions (0.0 to 2.0)
- performance_history: List of scores from this session

# Instructions
Determine the next interview state and phase transition.

**Phase Transitions**:
1. **Intro Phase** → Experience Phase:
   - After 2 questions (indices 0-1)
   - Always transition

2. **Experience Phase** → Technical Phase:
   - After 3 questions (indices 2-4)
   - Check performance:
     - Avg score > 1.5 → High performer
     - Avg score 0.0-1.5 → Adjust difficulty or skip to next

3. **Technical Phase** → Behavioral Phase:
   - After 5 questions (indices 5-9)
   - Performance-based adaptation:
     - Strong performance (avg > 7.0): Move to conclusion early or add more technical
     - Normal performance: Continue to behavioral

4. **Behavioral Phase** → Conclusion Phase:
   - Starts with 10 questions (10-19)
   - Evaluate overall progress

5. **Conclusion Phase**: 
   - Fill remaining questions (20-22)
   - Generate context-aware questions about the company and role

**Adaptation Rules**:

**For High Performers**:
- Slightly increase difficulty level
- Consider moving to conclusion earlier (reduce some technical questions)
- Focus on more specific/experiential questions

**For Low Performers**:
- Reduce difficulty level
- Ask more foundational questions
- Consider staying in technical phase longer if struggling

**Question Number Calculation**:
- Current question number + 1 = next question index
- Track cumulative total for progress tracking

**Output Requirements**:
- Determine next phase
- Determine next question count
- Determine appropriate difficulty level (1, 2, or 3)
- Return evaluation summary

# Constraints
- Max question number is 22 (23 questions total: 2+3+5+3+10)
- Don't skip phases without reason
- Base difficulty on performance but don't oscillate wildly
- Stay within phase bounds (don't enter conclusion too early or technical too late)

# Output Format
```json
{
  "next_phase": "Name of next phase",
  "next_phase_question_start": 5,
  "next_phase_question_count": 3,
  "next_difficulty_level": "1 or 2 or 3",
  "notes": ["Brief observations about performance"],
  "should_evaluate_phase": true
}
```

# Examples

**Example 1 - Normal Progression**:
**Input**:
- job_role="Software Engineer",
- current_phase="intro",
- current_question_number=1,
- total_questions_in_phase=2,
- overall_score=1.2,
- performance_history=[1.5, 0.9]

**Output**:
```json
{
  "next_phase": "experience",
  "next_phase_question_start": 2,
  "next_phase_question_count": 3,
  "next_difficulty_level": "2",
  "notes": ["Moderate performance, continuing with medium difficulty"],
  "should_evaluate_phase": false
}
```

**Example 2 - High Performer**:
**Input**:
- job_role="Software Engineer",
- current_phase="technical",
- current_question_number=7,
- total_questions_in_phase=5,
- overall_score=1.6,
- performance_history=[0.8, 1.7, 2.0, 1.8, 1.6]

**Output**:
```json
{
  "next_phase": "behavioral",
  "next_phase_question_start": 10,
  "next_phase_question_count": 3,
  "next_difficulty_level": "3",
  "notes": ["Consistently strong performance, recommending hard difficulty"],
  "should_evaluate_phase": true
}
```

**Example 3 - Low Performer**:
**Input**:
- job_role="Software Engineer",
- current_phase="technical",
- current_question_number=5,
- total_questions_in_phase=5,
- overall_score=0.5,
- performance_history=[0.7, 0.3, 0.6, 0.4, 0.5]

**Output**:
```json
{
  "next_phase": "behavioral",
  "next_phase_question_start": 10,
  "next_phase_question_count": 3,
  "next_difficulty_level": "1",
  "notes": ["Struggling with technical questions, reducing difficulty"],
  "should_evaluate_phase": true
}
```

**Example 4 - Beginning of Session**:
**Input**:
- job_role="Software Engineer",
- current_phase="intro",
- current_question_number=0,
- total_questions_in_phase=2,
- overall_score=0.0,
- performance_history=[]

**Output**:
```json
{
  "next_phase": "experience",
  "next_phase_question_start": 2,
  "next_phase_question_count": 3,
  "next_difficulty_level": "1",
  "notes": ["Beginning session, starting with easy questions"],
  "should_evaluate_phase": false
}
```

**Example 5 - Phase Complete**:
**Input**:
- job_role="Software Engineer",
- current_phase="technical",
- current_question_number=9,
- total_questions_in_phase=5,
- overall_score=1.3,
- performance_history=[1.0, 1.2, 1.5, 1.4, 1.3]

**Output**:
```json
{
  "next_phase": "behavioral",
  "next_phase_question_start": 10,
  "next_phase_question_count": 3,
  "next_difficulty_level": "2",
  "notes": ["Technical phase complete, transitioning to behavioral questions"],
  "should_evaluate_phase": true
}