# Manage Interview Flow

# Purpose
Determine the next phase and difficulty level for the interview based on current state and performance tracking.

# Inputs
- job_role: Target job role (e.g., "Software Engineer")
- current_phase: Current phase (e.g., "intro", "experience", "technical", "behavioral", "conclusion")
- current_question_number: Current question number (1-indexed)
- total_questions: Total questions for the entire interview
- phase_allocation: How many questions are allocated to each phase (e.g., "intro: 2, experience: 3, technical: 3, behavioral: 2")
- overall_score: Score for the just-evaluated question (0.0 to 10.0)
- performance_history: List of scores from previous questions in this session

# Instructions
Determine the next interview phase and difficulty level based on progress and performance.

**Phase Allocation**:
{{phase_allocation}}

**Transition Rules**:
- Each phase has an allocated number of questions shown above
- Use the ratio of questions answered in the current phase vs its allocation to decide transitions
- If you've answered >= 80% of allocated questions in the current phase, consider advancing to the next phase
- Adapt based on performance: high scores may justify advancing faster, low scores may justify staying longer
- Do not skip phases — always follow intro → experience → technical → behavioral → conclusion

**Adaptation Rules**:
- **High performers** (overall_score > 7.0): Consider advancing to next phase sooner, increase difficulty
- **Low performers** (overall_score < 5.0): Consider staying in current phase longer, decrease difficulty
- **Normal performance**: Follow the allocated phase plan

**Difficulty Levels**: 1 (Easy), 2 (Medium), 3 (Hard)

# Constraints
- Stay within total_questions={{total_questions}} total questions
- Don't skip phases without reason
- Base difficulty on performance but don't oscillate wildly
- Keep phase order natural (intro → experience → technical → behavioral → conclusion)

# Output Format
```json
{
  "next_phase": "Name of next phase",
  "next_difficulty_level": "1 or 2 or 3",
  "notes": ["Brief observations about performance"],
  "should_evaluate_phase": true
}
```

# Actual Data

- **Job Role**: {{job_role}}
- **Current Phase**: {{current_phase}}
- **Current Question Number**: {{current_question_number}}
- **Total Questions**: {{total_questions}}
- **Overall Score**: {{overall_score}}
- **Performance History**: {{performance_history}}

# Examples

**Example 1 - Normal Progression**:
**Input**:
- current_phase="intro"
- current_question_number=2
- total_questions=10
- phase_allocation="intro: 2, experience: 3, technical: 3, behavioral: 2"
- overall_score=6.0
- performance_history=[7.5, 4.5]

**Output**:
```json
{
  "next_phase": "experience",
  "next_difficulty_level": "2",
  "notes": ["Moderate performance in intro, advancing to experience with medium difficulty"],
  "should_evaluate_phase": false
}
```

**Example 2 - High Performer Advancing Early**:
**Input**:
- current_phase="technical"
- current_question_number=5
- total_questions=10
- phase_allocation="intro: 2, experience: 3, technical: 3, behavioral: 2"
- overall_score=8.5
- performance_history=[4.0, 8.5, 10.0, 9.0, 8.5]

**Output**:
```json
{
  "next_phase": "behavioral",
  "next_difficulty_level": "3",
  "notes": ["Consistently strong performance in technical, advancing to behavioral with increased difficulty"],
  "should_evaluate_phase": true
}
```
