# Interview Agent - Example Requests & Responses

## Overview
This document shows real examples of how the enhanced human-like interview system works.

## Example 1: Full Interview Workflow

### Request
```json
{
  "job_role": "Backend Developer",
  "candidate_answer": "I have experience with Laravel API development"
}
```

### Response (Natural Conversational Question)
```json
{
  "job_role": "Backend Developer",
  "question": "Can you walk me through a project where you had to optimize an API endpoint or database query? What was the challenge and how did you approach it?",
  "candidate_answer": "I have experience with Laravel API development",
  "company_context": "Key Requirements for Backend Developer:\n- Required skills:\n  Laravel\n  MySQL\n  REST API\n  Docker\n\n- Interview criteria:\n  Problem solving 40%\n  Technical knowledge 40%\n  Communication 20%",
  "feedback": "Score: 4/10\n\nYou've mentioned relevant experience, but your answer doesn't really show me what you've done. Here's my honest feedback:\n\n**What you did well:**\n- You stated relevant experience with Laravel, which is exactly what we need\n\n**Areas for growth:**\n- You gave a one-liner when I was asking for a detailed story. In interviews, when someone asks \"walk me through,\" they want to hear how you think and solve problems\n- You didn't mention any specific challenges or how you overcame them\n- No mention of tools, methodologies, or the actual outcome\n\n**What would help:**\nIf I asked again, share: the problem you faced, the steps you took to debug/optimize it, what you learned, and the impact. That's how we can understand if you're a good fit.\n\n**Next question I'd ask:**\nWhat's the most complex technical problem you've solved in Laravel? Take me through it.",
  "interview_complete": true
}
```

**Why this is better:**
- ✅ Question sounds natural: "Can you walk me through..." (not "List 5 steps...")
- ✅ Feedback is human-like: "Here's my honest feedback" (not a robotic score breakdown)
- ✅ Follow-up is conversational: "What's the most complex technical problem..." (continues natural flow)

---

## Example 2: Evaluate Answer + Get Follow-Up

### Request
```json
{
  "job_role": "Backend Developer",
  "question": "Tell me about a time you had to debug a complex performance issue.",
  "candidate_answer": "I used Laravel Debugbar to identify N+1 queries and then implemented eager loading with the with() method. This reduced database calls from 20+ to just 2 queries. The page load time went from 5 seconds to 800ms.",
  "company_context": "Backend Developer requirements: MySQL, Docker, REST APIs, Problem solving (40%), Technical knowledge (40%)"
}
```

### Response
```json
{
  "job_role": "Backend Developer",
  "question": "Tell me about a time you had to debug a complex performance issue.",
  "candidate_answer": "I used Laravel Debugbar to identify N+1 queries and then implemented eager loading with the with() method. This reduced database calls from 20+ to just 2 queries. The page load time went from 5 seconds to 800ms.",
  "evaluation": "Score: 8/10\n\nNow THIS is what I'm looking for. You clearly know your tools and you showed concrete results.\n\n**What impressed me:**\n- You used the right debugging tool for the job (Debugbar)\n- You identified the specific problem (N+1 queries)\n- You explained your solution clearly\n- You quantified the impact (specific numbers)\n- You showed technical depth with eager loading knowledge\n\n**Where you could go deeper:**\n- Did you consider other solutions? Why was eager loading the best choice?\n- What if the query was still slow after this? What would be next?\n\n**My impression:**\nYou have solid technical knowledge and a good problem-solving approach. You know Laravel well.",
  "suggested_follow_up": "So after you optimized those queries, did you run into any other bottlenecks with that endpoint? Sometimes there's more than one issue to solve."
}
```

**What's happening here:**
- ✅ Evaluation is conversational: "Now THIS is what I'm looking for" (real interviewer praise)
- ✅ Follow-up digs deeper: "did you run into any other bottlenecks" (natural continuation)
- ✅ Not scripted: Treats good answers better than bad ones

---

## Example 3: Multi-Turn Follow-Up

### Request (Continuing from Example 2)
```json
{
  "job_role": "Backend Developer",
  "previous_question": "So after you optimized those queries, did you run into any other bottlenecks with that endpoint?",
  "previous_answer": "Actually yes. Even with the query optimization, the response was still slow sometimes. I found the API was being called multiple times by the frontend because there was no caching. I implemented Redis caching with a 5-minute TTL and it solved the issue.",
  "company_context": "Backend Developer requirements: MySQL, Docker, REST APIs"
}
```

### Response
```json
{
  "job_role": "Backend Developer",
  "previous_question": "So after you optimized those queries, did you run into any other bottlenecks with that endpoint?",
  "previous_answer": "Actually yes. Even with the query optimization, the response was still slow sometimes. I found the API was being called multiple times by the frontend because there was no caching. I implemented Redis caching with a 5-minute TTL and it solved the issue.",
  "follow_up_question": "That's a good layered approach to optimization. How did you decide on the 5-minute TTL? Did you have to invalidate the cache for certain operations?"
}
```

**This is natural interviewing:**
- ✅ Shows genuine interest: "That's a good layered approach"
- ✅ Specific follow-up: Asks about the TTL decision and cache invalidation
- ✅ Continues conversation naturally

---

## Example 4: Interview with Weak Answer

### Request
```json
{
  "job_role": "Backend Developer",
  "question": "Tell me about a time you had to debug a complex performance issue.",
  "candidate_answer": "I know that performance is important. I always try to write good code.",
  "company_context": "Backend requirements"
}
```

### Response
```json
{
  "evaluation": "Score: 2/10\n\nI appreciate that you understand performance is important, but you didn't really answer my question. Let me be direct:\n\n**What I was looking for:**\nA specific story - a problem you actually faced, how you debugged it, what you did to fix it.\n\n**What you gave me:**\nGeneral statements about best practices.\n\n**The difference:**\nWhen I ask \"Tell me about a time,\" I want details that show how you think. \"I always try to write good code\" could mean anything and doesn't prove you can actually debug a performance issue.\n\n**To improve for next time:**\nThink about a real project where something was slow. What was it? How did you find the problem? What tools did you use? What was the result?\n\n**My impression:**\nI'm not confident you have hands-on experience with performance optimization. This is a core part of the job.",
  "suggested_follow_up": "Have you ever actually had to fix something that was slow in production? Tell me about that situation."
}
```

**Why this works:**
- ✅ Honest but not mean: "I appreciate that... but you didn't really answer"
- ✅ Clear: Explains exactly what was wrong and why
- ✅ Actionable: Gives specific guidance for improvement
- ✅ Shows the standard: Makes clear what a good answer looks like

---

## Key Differences: This System vs. Formal Interview Systems

| Aspect | This System | Formal Systems |
|--------|-----------|-----------------|
| Questions | "Walk me through a project..." | "List 5 principles of database indexing" |
| Tone | Conversational, curious | Scripted, robotic |
| Feedback | Human-like, specific | Numerical scores, generic |
| Follow-ups | Natural continuations | Predetermined questions |
| Evaluation | Considers context, gives guidance | Binary scoring |
| Interaction | Feels like real interview | Feels like questionnaire |

---

## Testing the System

### Step 1: Upload Documents
```bash
curl -X POST "http://localhost:8000/upload-document" \
  -F "file=@backend_guidelines.pdf"
```

### Step 2: Create Knowledge Base
```bash
curl -X POST "http://localhost:8000/create-knowledge-base"
```

### Step 3: Run Interview
```bash
curl -X POST "http://localhost:8000/interview" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Backend Developer",
    "candidate_answer": "I have experience with Laravel"
  }'
```

### Step 4: Get Evaluation with Follow-Up
```bash
curl -X POST "http://localhost:8000/interview/evaluate-with-followup" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Backend Developer",
    "question": "Tell me about optimizing an API.",
    "candidate_answer": "I used eager loading in Laravel...",
    "company_context": "MySQL, Docker, REST APIs"
  }'
```

---

## What Makes Questions Conversational?

### Good (Natural) ✅
- "Can you walk me through a project where you made a tough call?"
- "What's the hardest technical problem you've solved?"
- "Tell me about a time when something broke in production."
- "How do you approach debugging?"

### Bad (Formal) ❌
- "Define microservices architecture."
- "List 5 benefits of containerization."
- "What are the ACID properties of databases?"
- "Explain the MVC pattern in 3 bullet points."

The system is trained to generate good conversational questions automatically.

---

## Next Steps

1. **Test with your own documents** - Upload your company guidelines
2. **Create multiple interview scenarios** - Different job roles, levels
3. **Iterate based on feedback** - Adjust company context for better questions
4. **Use for screening** - Pre-interview evaluation before speaking with recruiter
5. **Use for training** - Practice common interview questions

Enjoy the realistic interview experience!
