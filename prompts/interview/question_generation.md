# Generate Interview Question

# Purpose
Generate a professional interview question based on the interview phase and job role context.

# Inputs
- job_role: Target job role (e.g., "Software Engineer", "Data Scientist")
- phase: Current interview phase (e.g., "intro", "experience", "technical", "behavioral", "conclusion")
- difficulty_level: Current difficulty level (1=easy, 2=medium, 3=hard)
- company_context: Company requirements and domain (optional)

# Instructions
Generate ONE interview question for this phase and difficulty level.

**Phase-Specific Guidance**:
- **intro**: Build rapport, understand background, assess career trajectory
- **experience**: Evaluate practical experience, methodologies, tools used
- **technical**: Test core technical knowledge, problem-solving, best practices
- **behavioral**: Assess soft skills, teamwork, conflict resolution, motivation
- **conclusion**: Final assessment, why this company, career goals

**Difficulty Levels**:
- **1 (Easy)**: Basic/Foundational knowledge, common in the field
- **2 (Medium)**: Intermediate application, requires some experience
- **3 (Hard)**: Advanced/Complex scenarios, requires expertise

**Style Requirements**:
- Natural, conversational language
- About 30-50 words
- Open-ended (invite detailed responses)
- Relevant to the job role
- 1-3 sentences only
- Connect to company context if provided

# Constraints
- Generate exactly ONE question
- No vague questions
- No questions requiring yes/no or one-word answers
- Don't ask generic questions like "Tell me about yourself" for technical phase
- Don't use corporate language or formality

# Output Format
Return ONLY the question text, prefixed with "Question: ". No JSON, no explanation.

Example:
Question: How would you approach designing a system for handling millions of concurrent users with minimal latency?

# Actual Data

- **Job Role**: {{job_role}}
- **Interview Phase**: {{phase}}
- **Difficulty Level**: {{difficulty_level}}
- **Company Context**: {{company_context}}
- **Candidate Profile**: {{candidate_profile}}
- **Question Number**: {{question_number}}
- **Conversation History**: {{conversation_history}}
