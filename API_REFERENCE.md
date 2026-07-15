# Quick Reference - API Usage Guide

## Starting the Server

```bash
# Start with hot reload (development)
uvicorn app.main:app --reload

# Start without hot reload (production)
uvicorn app.main:app

# Access API documentation
http://localhost:8000/docs
```

---

## Core Workflow

### 1. Upload Document
```bash
curl -X POST "http://localhost:8000/upload-document" \
  -F "file=@your_document.pdf"
```

**Response:**
```json
{
  "message": "Document uploaded",
  "filename": "your_document.pdf"
}
```

### 2. Create Knowledge Base
```bash
curl -X POST "http://localhost:8000/create-knowledge-base"
```

**Response:**
```json
{
  "message": "Knowledge base created",
  "chunks": 42
}
```

### 3. Run Full Interview
```bash
curl -X POST "http://localhost:8000/interview" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Backend Developer",
    "candidate_answer": "I have experience with Laravel APIs"
  }'
```

**Response:**
```json
{
  "job_role": "Backend Developer",
  "question": "Can you walk me through a project where...",
  "candidate_answer": "I have experience with Laravel APIs",
  "company_context": "Key Requirements for Backend Developer: ...",
  "feedback": "Score: X/10. Here's what I think...",
  "interview_complete": true
}
```

---

## Multi-Turn Interviews

### Option A: Evaluate + Get Follow-Up (Recommended)
One API call gets both evaluation and next question:

```bash
curl -X POST "http://localhost:8000/interview/evaluate-with-followup" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Backend Developer",
    "question": "Tell me about optimizing a slow API.",
    "candidate_answer": "I used eager loading to reduce queries.",
    "company_context": "Backend requirements: MySQL, Docker, Laravel"
  }'
```

**Response:**
```json
{
  "job_role": "Backend Developer",
  "question": "Tell me about optimizing a slow API.",
  "candidate_answer": "I used eager loading to reduce queries.",
  "evaluation": "Score: 7/10. You showed technical knowledge...",
  "suggested_follow_up": "How did you test that the optimization actually worked?"
}
```

### Option B: Generate Follow-Up Question
Get next question based on previous exchange:

```bash
curl -X POST "http://localhost:8000/interview/follow-up" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Backend Developer",
    "previous_question": "Tell me about optimizing a slow API.",
    "previous_answer": "I used eager loading to reduce queries.",
    "company_context": "MySQL, Docker, Laravel"
  }'
```

**Response:**
```json
{
  "follow_up_question": "How did you identify that queries were the bottleneck?"
}
```

---

## Quick Start Examples

### Example 1: Simple Question & Answer (No Multi-Turn)
```bash
# Just ask the initial question, get evaluation
curl -X POST "http://localhost:8000/interview" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Frontend Engineer",
    "candidate_answer": "I built React applications"
  }'
```

### Example 2: Complete Interview Flow
```bash
# 1. Get initial evaluation + follow-up suggestion
curl -X POST "http://localhost:8000/interview/evaluate-with-followup" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Frontend Engineer",
    "question": "Tell me about a complex state management challenge.",
    "candidate_answer": "I used Redux to manage global state in a large app.",
    "company_context": "React, TypeScript, Redux, CSS-in-JS"
  }'

# Response includes:
# - evaluation: feedback on their answer
# - suggested_follow_up: next question to ask

# 2. Ask follow-up, get their answer
# (Candidate provides: "I implemented Redux Thunk for async actions...")

# 3. Get evaluation + next follow-up
curl -X POST "http://localhost:8000/interview/evaluate-with-followup" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Frontend Engineer",
    "question": "How did you implement async actions?",
    "candidate_answer": "I implemented Redux Thunk for async actions...",
    "company_context": "React, TypeScript, Redux"
  }'
```

### Example 3: Multi-Role Screening
```bash
# Screen candidates for multiple roles from same company
roles=("Frontend Engineer" "Backend Developer" "DevOps Engineer")

for role in "${roles[@]}"; do
  curl -X POST "http://localhost:8000/interview" \
    -H "Content-Type: application/json" \
    -d "{
      \"job_role\": \"$role\",
      \"candidate_answer\": \"Tell them your relevant experience\"
    }"
done
```

---

## Optional Parameters

### Company Context
If you don't provide company_context, the system will try to retrieve it from the knowledge base:

```bash
# With explicit context
{
  "job_role": "Backend Developer",
  "candidate_answer": "...",
  "company_context": "Uses Python, Django, PostgreSQL, Docker..."
}

# Without context (retrieves from KB)
{
  "job_role": "Backend Developer",
  "candidate_answer": "..."
}
```

---

## Response Formats

### Interview Response
```json
{
  "job_role": "string",
  "question": "string (the interview question)",
  "candidate_answer": "string (what candidate said)",
  "company_context": "string (relevant company info)",
  "feedback": "string (evaluation and next steps)",
  "interview_complete": "boolean"
}
```

### Evaluation with Follow-Up Response
```json
{
  "job_role": "string",
  "question": "string (the question asked)",
  "candidate_answer": "string (their answer)",
  "evaluation": "string (score and feedback)",
  "suggested_follow_up": "string (next question)"
}
```

### Follow-Up Response
```json
{
  "job_role": "string",
  "previous_question": "string",
  "previous_answer": "string",
  "follow_up_question": "string (next question)"
}
```

---

## Error Handling

### Missing Required Fields
```json
{
  "error": "job_role is required"
}
```

### Vector Database Not Found
```json
{
  "error": "Vector database not found. Run /create-knowledge-base first"
}
```

### API Key Not Set
```json
{
  "error": "OPENROUTER_API_KEY environment variable not set"
}
```

---

## Tips & Best Practices

### 1. Upload Relevant Documents
Upload PDFs that contain:
- Job role requirements
- Company values and culture
- Technical skills needed
- Evaluation criteria
- Team structure

The system will use this to ask contextual questions.

### 2. Use Evaluate-with-FollowUp for Efficiency
```bash
# Good - One API call, get evaluation + next question
POST /interview/evaluate-with-followup

# Less efficient - Two separate calls
POST /interview/evaluate-with-followup  # Get evaluation
POST /interview/follow-up              # Get next question
```

### 3. Keep Company Context Consistent
Use same `company_context` across multi-turn interview:
```bash
# All turns use same context for consistency
company_context = "Backend Dev: Python, Django, PostgreSQL, Docker"

# Turn 1
POST /interview/evaluate-with-followup
  company_context: company_context

# Turn 2  
POST /interview/evaluate-with-followup
  company_context: company_context
```

### 4. Track Interview Progress
Maintain state on client side:
```json
{
  "interview": {
    "role": "Backend Developer",
    "start_time": "2024-01-15T10:00:00",
    "questions": [
      {
        "question": "Q1...",
        "answer": "A1...",
        "evaluation": "Good"
      },
      {
        "question": "Q2...",
        "answer": "A2...",
        "evaluation": "Excellent"
      }
    ],
    "overall_score": 7.5
  }
}
```

### 5. Customize for Different Stages
```bash
# Phone screening - shorter answers expected
POST /interview/evaluate-with-followup
  company_context: "Basic technical screening"

# Technical interview - deeper answers expected
POST /interview/evaluate-with-followup
  company_context: "Complete technical evaluation with system design"

# Culture fit - soft skills focus
POST /interview/evaluate-with-followup
  company_context: "Culture, teamwork, communication focus"
```

---

## Testing

### Manual Test via Swagger UI
1. Start server: `uvicorn app.main:app --reload`
2. Go to: `http://localhost:8000/docs`
3. Find `/interview/evaluate-with-followup`
4. Click "Try it out"
5. Fill in example data
6. See response in real-time

### Automated Test
```bash
python test_interview_system.py
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No vector database" | Run `/create-knowledge-base` with a PDF in `documents/` |
| "API key not found" | Create `.env` file with `OPENROUTER_API_KEY=your_key` |
| Slow response | API calls to OpenRouter may take 5-30 seconds, depending on load |
| Generic questions | Upload company PDFs with more specific requirements |
| Weak feedback | Ensure `company_context` is provided for better evaluation |

---

## Rate Limiting

The system makes API calls to OpenRouter. To avoid rate limits:
- Don't run more than 5 concurrent interviews
- Space out requests by 1+ second
- Monitor API usage in your OpenRouter dashboard

---

## Support

Need help?
1. Check `EXAMPLES.md` for detailed examples
2. Check `ENHANCEMENTS.md` for what's new
3. Check `README.md` for full documentation
4. Run `test_interview_system.py` to see system in action

Enjoy conducting natural, human-like interviews! 🎯
