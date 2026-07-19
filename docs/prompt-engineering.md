# AI Interview Agent - Prompt Engineering

## Overview

This document describes the prompt management strategy for the AI Interview Agent. It covers why prompts should be externalized, how to structure them, and best practices for engineering effective prompts.

## Why Externalize Prompts?

### Problems with Current Approach

**❌ Current Issues**:
```python
# bad/prompts/in_api.py (example)
def company_evaluate_with_followup(data):
    evaluation_prompt = f"""
    You are an experienced technical interviewer.
    
    Company ID: {data.get("company_id")}
    Job Role: {data.get("job_role")}
    Question: {data.get("question")}
    Candidate Answer: {data.get("candidate_answer")}
    
    Evaluate the answer.
    
    Format:
    **Score:** X / 10
    
    **Strengths**
    -
    
    **Growth Areas**
    -
    
    Be honest and constructive.
    
    """
    
    # ... LLM call
```

**Problems**:
- Prompts embedded in Python files - violates separation of concerns
- Not in version control as markdown
- Cannot easily iterate on prompts without code changes
- Hard to A/B test different prompt styles
- Not documented

### Benefits of Externalized Prompts

**✅ Externalized Approach**:
```python
# prompts/interview/answer_evaluation.md
# Purpose: Evaluate candidate answers with feedback

# Inputs
- job_role: Target job role
- question: The question asked
- candidate_answer: The candidate's response
- company_context: Company requirements (optional)

# Instructions
You are an experienced technical interviewer evaluating a candidate...
... detailed instructions

# Output Format
{
  "overall_score": 0.5 to 2.0,
  "technical_score": 0.0 to 2.0,
  "communication_score": 0.0 to 2.0,
  "strengths": ["array"],
  "weaknesses": ["array"],
  "suggested_follow_up": "string",
  "feedback_detail": "string"
}
```

**Benefits**:
- **Version Control**: Prompts can be committed, reviewed, and rolled back
- **Documentation**: Each prompt is self-documenting
- **Iteration**: Can modify prompts in markdown files without redeploying code
- **Collaboration**: Team members can review and improve prompts
- **Testing**: Can test different prompts independently
- **A/B Testing**: Can easily test prompt variants

## Prompt File Structure

### Required Sections

Every prompt file must include these sections:

1. **# Purpose** - What this prompt does
2. **# Inputs** - What context/data the prompt receives
3. **# Constraints** - Rules the LLM must follow
4. **# Instructions** - Step-by-step instructions for the LLM
5. **# Output Format** - Expected output structure
6. **# Examples** - Few-shot examples if applicable

### Example Template

```markdown
# [Prompt Name]

# Purpose
[Brief description of what this prompt does and why]

# Inputs
- input1: Description of input1
- input2: Description of input2
- input3: Description of input3 (optional)

# Constraints
1. Constraint 1: Must follow this rule
2. Constraint 2: Must follow this rule
3. Do NOT do: This is forbidden

# Instructions
Follow these steps:

Step 1: [First instruction]
Step 2: [Second instruction]
...

Be conversational and professional.
Use clear, concise language.

# Output Format
[Detailed structure with example]

**Example Output**:
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

# Examples (Few-Shot)

**Example 1**: [Describe scenario]
Input: [Describe input]
Expected Output: [Show expected output]

**Example 2**: 
Input: [Describe input]
Expected Output: [Show expected output]
```

## Current Prompt Inventory

### System Prompts

1. **interviewer_system.md** - Defines interviewer persona
2. **evaluator_system.md** - Defines evaluator behavior
3. **followup_system.md** - Defines follow-up question generation

### Interview Prompts

1. **question_generation.md** - Generates interview questions
2. **adaptive_question.md** - Adapts questions based on difficulty
3. **interview_flow.md** - Manages interview flow/state

### Evaluation Prompts

1. **answer_evaluation.md** - Evaluates candidate answers
2. **scoring_rules.md** - Defines scoring criteria

## Prompt Categories

### 1. System Prompts

**Purpose**: Define agent persona and core behavior

**Example: interviewer_system.md**
```markdown
# Interviewer System

# Purpose
Define the persona and behavior of the AI interviewer.

# Instructions
You are a professional, empathetic interviewer conducting a real job interview.

**Tone**:
- Conversational, not robotic
- Professional and respectful
- Curious and engaged
- Realistic and authentic

**Style**:
- Ask natural, open-ended questions
- Build rapport with the candidate
- Demonstrate genuine interest in their experience
- Avoid scripted or formal language
- Welcome details and examples

**Do NOT**:
- Use formal, corporate language
- Quiz the candidate
- Use flowery or exaggerated language
- Ask generic questions from a list

**Do**:
- Sound like you're actually having a conversation
- Connect questions to the candidate's responses
- Invite expansion on their ideas
- Accept that the conversation will flow naturally
```

### 2. Task-Specific Prompts

**Purpose**: Generate specific outputs (questions, evaluations, etc.)

**Example: question_generation.md**
```markdown
# Generate Interview Question

# Purpose
Generate a professional interview question based on the phase and context.

# Inputs
- job_role: Target job role (e.g., "Software Engineer")
- phase: Current interview phase (e.g., "technical", "intro")
- difficulty_level: Difficulty (1=easy, 2=medium, 3=hard)
- conversation_history: Previous conversation (optional)

# Instructions
Generate ONE interview question.

Focus:
- {Phase context from configuration}

Difficulty:
- Difficulty {difficulty_level} means:
  * 1: Basic/Foundational knowledge
  * 2: Intermediate application
  * 3: Advanced/Complex scenarios

Style:
- Natural and conversational
- About 1-3 sentences
- Open-ended (invite details)
- ~30-50 words
- Build on conversation if history available

Examples:
"{Example questions from configuration}"

Generate the question now.
```

### 3. Response-Based Prompts

**Purpose**: Generate responses based on candidate input

**Example: answer_evaluation.md**
```markdown
# Evaluate Candidate Answer

# Purpose
Evaluate a candidate's answer with detailed feedback and suggested follow-up.

# Inputs
- job_role: Target job role (e.g., "Software Engineer")
- question: The question asked
- candidate_answer: The full candidate response
- phase: Current interview phase
- difficulty_level: Question difficulty

# Instructions
Evaluate the candidate's answer as if you're providing honest, constructive feedback to the candidate.

**Scoring Guide**:
- 2.0: Excellent - Demonstrates mastery, provides specific examples
- 1.5: Good - Solid understanding, minor gaps
- 1.0: Fair - Understanding exists, but incomplete or generic
- 0.5: Poor - Missing key points, inaccurate understanding

**Evaluation Criteria**:
1. Technical Knowledge - Depth and accuracy
2. Problem Solving - Approach and logic
3. Communication - Clarity and structure
4. Overall Impression - Whether they belong in this role

**Output in JSON format**:
```json
{
  "overall_score": 0.0-2.0,
  "technical_score": 0.0-2.0,
  "communication_score": 0.0-2.0,
  "strengths": ["detailed example", "another strength"],
  "weaknesses": ["detailed example", "another weakness"],
  "suggested_follow_up": "A natural follow-up question that digs deeper",
  "feedback_detail": "Comprehensive feedback (3-5 sentences)"
}
```

Include ALL scores. Use floats. Round to 0.1 precision.
```

## Prompt Engineering Best Practices

### 1. Use Clear, Precise Language

**❌ Vague**:
```markdown
Generate a good question for this role.
```

**✅ Precise**:
```markdown
Generate ONE interview question that:
- Is approximately 30-50 words
- Tests knowledge of {specific_concept}
- Requires 2-3 sentences to answer
- Can be answered by experienced developers
```

### 2. Use Constraints, Not "Try To"

**❌ Generally**:
```markdown
Be conversational and professional.
```

**✅ Explicit**:
```markdown
DO NOT:
- Use formal or corporate language
- Ask questions in a list format
- Include introductions like "The question is:"

DO:
- Sound like a natural human interviewer
- Ask questions that follow the previous response
- Use casual professional language
```

### 3. Provide Output Templates

**❌ Unclear**:
```markdown
Provide feedback.
```

**✅ Structured**:
```markdown
Output a score between 0 and 10, followed by:
**Strengths:**
- [bullet point 1]
- [bullet point 2]

**Weaknesses:**
- [bullet point 1]
- [bullet point 2]

**Suggested Follow-up:**
[any text without hash]

**Overall Assessment:**
[one sentence summary]
```

### 4. Use Few-Shot Prompting

**❌ No guidance**:
```markdown
Evaluate this answer:
{candidate_answer}

Now evaluate this one:
{candidate_answer}
```

**✅ Example-based**:
```markdown
Evaluate candidate answers:

**Example 1**:
Question: "Tell me about a time you had a conflict with a manager."
Answer: "Once I disagreed with my manager about a technical choice..."

Evaluation: "**Score:** 1.5/10\n\n**Strengths:**\n- Focused on the issue rather than personality\n\n**Weaknesses:**\n- Could have been more specific about the resolution\n\n**Suggested Follow-up:**\nHow did you ensure your technical reasoning was reflected in the final decision?"

---

Now evaluate this answer:
Question: "Tell me about a time you had a conflict with a manager."
Answer: "Once my manager wanted me to use a deprecated framework. I explained my reasoning thorough... and showed they had good results using the modern alternative. This taught me..."
```

### 5. Set Temperature Appropriately

Different tasks need different temperatures:

```python
# High creativity (interviewers, feedback)
temperature=0.7

# Moderate consistency (evaluations)
temperature=0.5

# Low randomness (extraction, formatting)
temperature=0.3

# Deterministic (code generation)
temperature=0.1
```

### 6. Split Long Context

**❌ Single massive prompt**:
```markdown
[Evaluate this question about Java, Python, JavaScript, React, Node.js... lots of requirements... lots of context... then evaluate this answer]
```

**✅ Split context**:
```markdown
# System Prompt
You are evaluating answers about {domain}.

# User Prompt
Question: {question}
Answer: {answer}
```

## Prompt Versioning

### Branching Strategy

For major prompt changes:
```bash
# Create feature branch for prompt improvements
git checkout -b feature/improve-evaluation-prompt

# Edit prompts/
vim prompts/interview/answer_evaluation.md

# Tests
pytest tests/test_prompts.py

# Commit with clear message
git commit -m "feat: improve evaluation prompt with structured JSON output

- Add explicit JSON output format
- Define scoring ranges clearly
- Add 3 example cases
- Add constraints for output format

Closes #42"
```

### Changelog

Maintain a CHANGELOG.md for prompts:
```markdown
## [1.2.0] - 2026-07-18

### Added
- Added `suggested_follow_up` field to evaluation responses
- Added structured JSON output requirement

### Changed
- Improved detailed feedback instructions
- Added temperature specification (0.5)

### Fixed
- Removed ambiguous formatting requirements
```

### Backward Compatibility

When changing prompt structure:
1. Maintain old format as "historical"
2. Document new format clearly
3. Support both formats in code
4. Add deprecation notice for old format

## Testing Prompts

### Unit Testing

```python
# tests/test_prompts/test_answer_evaluation.py
import pytest
from prompts.loader import PromptLoader
from app.services.interview_service import interview_service

@pytest.mark.asyncio
async def test_evaluation_prompt_structure():
    """Test that evaluation prompt has required sections"""
    loader = PromptLoader("prompts/interview/answer_evaluation.md")
    
    content = await loader.load({})
    
    # Required sections exist
    assert "# Purpose" in content
    assert "# Inputs" in content
    assert "# Instructions" in content
    assert "# Output Format" in content

@pytest.mark.asyncio
async def test_llm_response_format():
    """Test LLM returns valid JSON structure"""
    result = await interview_service.evaluate_answer(
        question="Test question",
        answer="Test answer",
        job_role="Software Engineer"
    )
    
    # assert required fields
    assert "overall_score" in result
    assert "technical_score" in result
    assert "communication_score" in result
    assert isinstance(result["strengths"], list)
    assert isinstance(result["weaknesses"], list)
    assert isinstance(result["suggested_follow_up"], str)

@pytest.mark.asyncio
async def test_evaluation_scoring_in_range():
    """Test scores are in valid range (0 to 2.0 for 0-10 scale)"""
    response = await interview_service.evaluate_answer(...)
    
    for score_field in ["overall_score", "technical_score", "communication_score"]:
        assert 0.0 <= response[score_field] <= 2.0
```

### A/B Testing

```python
# app/services/experiments.py
class PromptExperiment:
    """Track and compare prompt variants"""
    
    def __init__(self):
        self.variants = {
            "v1": "prompts/interview/answer_evaluation.md",
            "v2": "prompts/interview/answer_evaluation_v2.md"
        }
        self.results = {}
    
    async def run_comparison(self, test_cases):
        """Run same evaluation with both prompt variants"""
        for prompt_id, prompt_path in self.variants.items():
            results = []
            for test_case in test_cases:
                response = await self.evaluate_with_prompt(
                    prompt_path,
                    test_case
                )
                results.append(response)
            self.results[prompt_id] = results
        
        # Compare metrics
        self._compare_metrics()

prompt_experiment = PromptExperiment()
```

## Prompt Files Checklist

Before creating any prompt file, verify:

- [ ] Title starts with `# [Prompt Name]`
- [ ] `# Purpose` section exists and describes the prompt
- [ ] `# Inputs` section lists all inputs with descriptions
- [ ] `# Constraints` section has clear Do's and Don'ts
- [ ] `# Instructions` section is step-by-step
- [ ] `# Output Format` section has clear structure
- [ ] `# Example[s]` section has at least 2-3 examples
- [ ] Prompts are concise (not excessively long)
- [ ] Examples match expected output format
- [ ] All acronyms and technical terms are defined
- [ ] Language is natural, not corporate
- [ ] No embedded code or metadata
- [ ] Readable markdown formatting

## Common Mistakes to Avoid

### ❌ Mistake 1: Overly Vague Prompts
```markdown
Generate feedback about the answer.
```

**Better**:
```markdown
Evaluate this answer and provide:
1. An overall score (0-10)
2. 3-5 specific strengths
3. 3-5 specific areas for improvement
4. One sentence summary
```

### ❌ Mistake 2: Too Much Context
```markdown
This is a coffee shop🥝 in the town of Marais with one Barista. 
Everything about this shop relates to a coffee shop🥝. 

Customer Name: Long rambling paragraph about... extremely lengthy context...

Answer: Very long rambling paragraph...
```

**Better**:
```markdown
# Context
Question: "Describe a memorable customer experience."
Answer: "Recently, a customer ordered a latte with a specific request..."

# Task
Analyze this customer service example.
```

### ❌ Mistake 3: Conflicting Instructions
```markdown
DO:
- Generate concise answers (under 50 words)
- Include details

DO:
- Write comprehensive answers (100+ words)
- Cover all aspects
```

**Better**: Resolve conflicts explicitly.

### ❌ Mistake 4: Rigid Formatting Requirements
```markdown
Output format must be EXACTLY this:
```
[Complex multi-line template]
(With parentheses, quotes, indentation)
```
```

**Better**: Use examples to show format without being overly strict.

## Prompt Maintenance

### Regular Review Schedule

- **Weekly**: Scan all prompt files for clarity issues
- **Monthly**: Review prompt metrics and success rates
- **Quarterly**: Audit prompt performance and A/B test improvements
- **Annually**: Major prompt restructuring and optimization

### Performance Metrics

Track these metrics for each prompt:

```json
{
  "prompt_name": "answer_evaluation",
  "version": "1.2",
  "invocations": 1523,
  "success_rate": 99.7%,
  "avg_duration": 4500ms,
  "avg_tokens": 850,
  "scoring_consistency": 92%,
  "follow_up_quality": 4.2/5,
  "last_reviewed": "2026-07-18",
  "next_review": "2026-08-18"
}
```

## Transition Plan from Current to Externalized Prompts

### Phase 1: Investigation (Week 1)
1. List all hardcoded prompts in current codebase
2. Categorize prompts by type (system, task, etc.)
3. Create markdown prompt files for each

### Phase 2: Implementation (Phase 2 of refactoring)
1. Create `prompts/loader.py` - Prompt loader utility
2. Create `prompts/registry.py` - Register all prompts
3. Update APIs to load prompts from files
4. Maintain backward compatibility during transition
5. Add logging for prompt loading

### Phase 3: Testing (Week 2)
1. Test all interview flows with new prompts
2. Compare results with old prompts (A/B test)
3. Validate structured output quality
4. Fix any issues discovered

### Phase 4: Cleanup (Week 3)
1. Remove hardcoded prompts from code
2. Update documentation
3. Add prompt-specific unit tests
4. Deploy to production

## Resources for Learning Prompt Engineering

### Recommended Reading
- "In-Context Learning" by OpenAI
- "The Beauty and Power of Prompt Engineering" by Anthropic
- Prompt Engineering Guide: https://www.promptingguide.ai/

### Tools
- ChatGPT Playground (A/B test prompts)
- Claude Artifacts (test prompt outputs quickly)
- PromptPerfect (optimize prompts)
- LaMDA optimization tools

### Templates

See `prompts/` directory in this project for working templates.