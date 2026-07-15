# Developer's Guide - Customizing Your Interview System

This guide shows you how to customize the interview system to match your company's needs exactly.

## System Architecture

```
Request Flow:
┌─────────────────────────────────────────────────────┐
│ 1. HTTP Request                                     │
│    {job_role, candidate_answer, company_context}   │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ 2. Retrieval Agent (app/agents/retriever.py)       │
│    - Gets relevant context from vector DB          │
│    - Formats for human readability                 │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ 3. Interviewer Agent (app/agents/interviewer.py)   │
│    - Generates natural questions                   │
│    - Uses company context                          │
│    - Conversational tone                           │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ 4. Evaluator Agent (app/agents/evaluator.py)       │
│    - Evaluates candidate answer                    │
│    - Provides feedback                             │
│    - Suggests follow-up question                   │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ 5. HTTP Response                                    │
│    {evaluation, feedback, suggested_follow_up}     │
└─────────────────────────────────────────────────────┘
```

## Customizing Question Style

### Edit: `app/agents/interviewer.py`

The key is the `prompt` variable. Here's how to customize:

#### Current Approach (Natural/Conversational)
```python
prompt = f"""
You are an experienced technical interviewer...
Generate ONE natural, conversational interview question that:
1. Relates directly to real-world challenges
2. Invites the candidate to share practical experience
3. Sounds like something a real interviewer would ask
...
"""
```

#### Alternative Approach 1: Formal Interview
```python
prompt = f"""
You are a formal technical interviewer conducting a structured interview.

Role: {state["job_role"]}
Requirements: {state["company_context"]}

Generate a formal, structured interview question that:
1. Tests knowledge of core concepts
2. Is objective and measurable
3. Follows a standardized format

Format your question as: [QUESTION]: [DESCRIPTION]
"""
```

#### Alternative Approach 2: Behavioral Interview (STAR Method)
```python
prompt = f"""
You are a behavioral interviewer using the STAR method.

Role: {state["job_role"]}
Focus Areas: {state["company_context"]}

Generate a STAR-format question that asks the candidate about:
- Situation: What was happening
- Task: What they needed to do
- Action: What they did
- Result: What happened

Ask ONE clear behavioral question.
"""
```

#### Alternative Approach 3: Technical Depth Testing
```python
prompt = f"""
You are a technical depth interviewer.

Role: {state["job_role"]}
Required Skills: {state["company_context"]}

Generate a technical question that:
1. Tests deep understanding of core concepts
2. Requires specific technical knowledge
3. Has clear right/wrong answers

Ask ONE focused technical question.
"""
```

### Example: Customizing for Your Company

```python
def interview_agent(state):
    try:
        company_name = "Acme Corp"
        interview_style = "conversational"  # Change to "formal", "behavioral", etc.
        
        prompt_map = {
            "conversational": """You are an experienced interviewer...""",
            "formal": """You are a formal interviewer...""",
            "behavioral": """You use the STAR method...""",
            "technical": """You test deep technical knowledge..."""
        }
        
        base_prompt = prompt_map[interview_style]
        
        prompt = f"""{base_prompt}
        
For {company_name}, role: {state["job_role"]}
Requirements: {state["company_context"]}

Generate your question...
"""
        response = llm.invoke(prompt)
        state["question"] = response.content.strip()
        return state
        
    except Exception as e:
        logger.error(f"Error in interview_agent: {str(e)}")
        state["question"] = f"Error generating question: {str(e)}"
        return state
```

---

## Customizing Feedback Style

### Edit: `app/agents/evaluator.py`

The feedback system can be customized by changing the evaluation prompt:

#### Current Approach (Supportive/Coaching)
```python
prompt = f"""
You are an experienced technical interviewer evaluating a response.
Your feedback is constructive, honest, and helpful.

Provide feedback as:
1. Score: 1-10
2. What they did well
3. Areas for growth
4. Next step question
5. Overall impression

Write in a conversational, encouraging tone.
"""
```

#### Alternative Approach 1: Harsh/Realistic
```python
prompt = f"""
You are a demanding technical interviewer.

Evaluate the answer:
- Is it correct?
- Is it complete?
- Did they miss anything?
- Would you hire this person?

Be direct and honest. Don't sugarcoat.
"""
```

#### Alternative Approach 2: Structured Rubric
```python
prompt = f"""
You are an objective evaluator using a standardized rubric.

Score on these dimensions:
- Technical Accuracy (0-25 points)
- Communication (0-25 points)  
- Problem-Solving Approach (0-25 points)
- Relevant Experience (0-25 points)

Total Score: 0-100

Provide score and brief explanation for each.
"""
```

#### Alternative Approach 3: Skills Assessment Matrix
```python
prompt = f"""
Evaluate the candidate on:
- Coding ability: ★★★★☆
- System design: ★★★☆☆
- Communication: ★★★★☆
- Problem solving: ★★★★★

Provide short reason for each rating.
Overall hire recommendation: [YES/NO/MAYBE]
"""
```

---

## Adding New Agents

### Step 1: Create Agent File

Create `app/agents/cultural_fit.py`:

```python
import logging
from app.models.llm import llm

logger = logging.getLogger(__name__)

def cultural_fit_agent(state):
    """Evaluate candidate's cultural fit"""
    try:
        if not state.get('candidate_answer') or not state.get('job_role'):
            logger.warning("Missing required fields for cultural fit evaluation")
            state["cultural_fit_score"] = 0
            return state
        
        prompt = f"""
You are evaluating cultural fit for {state['job_role']} at our company.

Company Values: Innovation, Collaboration, Integrity, Customer Focus

Candidate Answer: {state['candidate_answer']}

Rate cultural fit 1-10 and explain why. Consider:
- Do they value collaboration?
- Do they show integrity?
- Are they customer-focused?

Provide: Score and brief explanation.
"""
        
        response = llm.invoke(prompt)
        state["cultural_fit_evaluation"] = response.content
        logger.info("Cultural fit evaluation completed")
        return state
        
    except Exception as e:
        logger.error(f"Error in cultural_fit_agent: {str(e)}")
        state["cultural_fit_evaluation"] = f"Error: {str(e)}"
        return state
```

### Step 2: Add to Workflow

Edit `app/graph/workflow.py`:

```python
from app.agents.cultural_fit import cultural_fit_agent

# Add to workflow
workflow.add_node("cultural_fit", cultural_fit_agent)

# Add connections (example: after evaluation)
workflow.add_edge("evaluator", "cultural_fit")
workflow.set_finish_point("cultural_fit")
```

### Step 3: Test

```bash
# Your new agent is now part of the workflow
curl -X POST "http://localhost:8000/interview" \
  -H "Content-Type: application/json" \
  -d '{"job_role": "Engineer", "candidate_answer": "..."}'
```

---

## Customizing the Workflow

### Current Flow
```
Retriever → Interviewer → Evaluator
```

### Example Custom Flow 1: Pre-Screening
```
Retriever → Interviewer → Evaluator → Cultural Fit Agent → Final Decision
```

### Example Custom Flow 2: Multi-Assessment
```
Retriever → Interviewer → Evaluator
         ├→ Technical Skills Assessment
         ├→ Cultural Fit Assessment
         └→ Communication Assessment
           → Aggregated Result
```

### Implementation Example

Edit `app/graph/workflow.py`:

```python
from langgraph.graph import StateGraph, END

# Define state with more fields
class InterviewState(TypedDict):
    job_role: str
    question: str
    candidate_answer: str
    company_context: str
    feedback: str
    technical_score: float
    cultural_fit_score: float
    overall_recommendation: str

# Create workflow
workflow = StateGraph(InterviewState)

# Add all agents
workflow.add_node("retriever", retrieval_agent)
workflow.add_node("interviewer", interview_agent)
workflow.add_node("technical", technical_assessment_agent)
workflow.add_node("cultural", cultural_fit_agent)
workflow.add_node("aggregator", aggregate_results_agent)

# Connect them
workflow.set_entry_point("retriever")
workflow.add_edge("retriever", "interviewer")
workflow.add_edge("interviewer", "technical")
workflow.add_edge("interviewer", "cultural")
workflow.add_edge("technical", "aggregator")
workflow.add_edge("cultural", "aggregator")
workflow.set_finish_point("aggregator")

graph = workflow.compile()
```

---

## Customizing Context/Prompts

### Example: Role-Specific Prompts

```python
ROLE_SPECIFIC_PROMPTS = {
    "Backend Developer": {
        "focus_areas": ["Architecture", "Databases", "Performance"],
        "interview_style": "conversational",
        "evaluation_rubric": "technical_heavy"
    },
    "Frontend Engineer": {
        "focus_areas": ["UX", "Performance", "Accessibility"],
        "interview_style": "behavioral",
        "evaluation_rubric": "balanced"
    },
    "DevOps Engineer": {
        "focus_areas": ["Infrastructure", "Automation", "Reliability"],
        "interview_style": "technical",
        "evaluation_rubric": "systems_heavy"
    }
}

def get_role_config(job_role):
    return ROLE_SPECIFIC_PROMPTS.get(
        job_role, 
        ROLE_SPECIFIC_PROMPTS["Backend Developer"]  # Default
    )
```

Use in interviewer agent:

```python
role_config = get_role_config(state["job_role"])
focus_areas = ", ".join(role_config["focus_areas"])

prompt = f"""
For {state['job_role']}, focus on: {focus_areas}
..."""
```

---

## Environment Configuration

Add to `.env`:

```env
# Interview Configuration
INTERVIEW_STYLE=conversational  # conversational, formal, behavioral
FEEDBACK_STYLE=supportive       # supportive, harsh, structured
MIN_SCORE=5                     # Minimum acceptable score
MAX_SCORE=10                    # Maximum possible score
```

Use in code:

```python
import os

INTERVIEW_STYLE = os.getenv("INTERVIEW_STYLE", "conversational")
FEEDBACK_STYLE = os.getenv("FEEDBACK_STYLE", "supportive")
MIN_SCORE = int(os.getenv("MIN_SCORE", "5"))
```

---

## Testing Your Customizations

### Unit Test Example

```python
# test_custom_agents.py
from app.agents.cultural_fit import cultural_fit_agent

def test_cultural_fit_agent():
    state = {
        "job_role": "Backend Developer",
        "candidate_answer": "I love collaborating with teams and learning new things."
    }
    
    result = cultural_fit_agent(state)
    
    assert "cultural_fit_evaluation" in result
    assert result["cultural_fit_evaluation"] != ""
    print("✅ Cultural fit agent working correctly")

if __name__ == "__main__":
    test_cultural_fit_agent()
```

### Integration Test Example

```python
# test_custom_workflow.py
from app.graph.workflow import graph

def test_full_interview_workflow():
    input_data = {
        "job_role": "Backend Developer",
        "candidate_answer": "I used Django with PostgreSQL"
    }
    
    result = graph.invoke(input_data)
    
    assert "feedback" in result
    assert "cultural_fit_evaluation" in result
    assert "technical_score" in result
    print("✅ Full workflow working correctly")

if __name__ == "__main__":
    test_full_interview_workflow()
```

---

## Performance Optimization

### Caching Evaluations

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_evaluation(question: str, answer: str, role: str):
    """Cache evaluations to avoid repeated API calls"""
    # ... evaluation logic
```

### Batch Processing

```python
# Process multiple candidates in parallel
from concurrent.futures import ThreadPoolExecutor

candidates = [
    {"job_role": "Backend", "answer": "Answer 1"},
    {"job_role": "Backend", "answer": "Answer 2"},
    {"job_role": "Frontend", "answer": "Answer 3"}
]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(evaluate_candidate, candidates))
```

---

## Monitoring & Logging

### Custom Logging

```python
# Log to file
import logging

handler = logging.FileHandler('interviews.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(handler)

# Use
logger.info(f"Interview completed: {state['job_role']} scored {score}/10")
```

### Track Metrics

```python
import json
from datetime import datetime

def log_interview_result(job_role, score, feedback):
    """Log interview results for analytics"""
    result = {
        "timestamp": datetime.now().isoformat(),
        "job_role": job_role,
        "score": score,
        "feedback_length": len(feedback)
    }
    with open("interview_results.jsonl", "a") as f:
        f.write(json.dumps(result) + "\n")
```

---

## Common Customizations

### Make Questions Easier
Reduce detail requirement in interviewer prompt

### Make Questions Harder  
Require deeper technical knowledge

### Change Scoring Scale
Modify from 1-10 to 1-5 or 1-100

### Add Role Levels
"Senior Backend" vs "Junior Backend" with different expectations

### Include Follow-Up Logic
"If score < 5, ask more basic questions"

### Add Time Tracking
Track how long candidates take to answer

---

## Best Practices

1. **Test changes locally first** - Use `test_interview_system.py`
2. **Keep prompts clear** - LLMs work better with explicit instructions
3. **Version your prompts** - Save old versions before changes
4. **Monitor results** - Track scores and feedback quality
5. **Iterate based on feedback** - Adjust prompts based on results
6. **Document customizations** - Explain why you made changes

---

## Help & Support

For questions:
1. Check the prompt in question closely
2. Look at EXAMPLES.md for working examples
3. Test with `test_interview_system.py`
4. Add logging to debug issues
5. Review LLM API documentation

Happy customizing! 🚀
