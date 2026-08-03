# Generate Interview Question

# Purpose
Generate ONE professional, open-ended interview question targeted at testing a specific competency and the current hypothesis about the candidate.

# Inputs
- job_role: Target job role (e.g., "Software Engineer", "Data Scientist")
- target_competency: The competency this question must probe (e.g., "tech_core", "system_design", "communication", "general")
- difficulty: Current difficulty level (1=easy, 2=medium, 3=hard)
- persona: Interviewer persona (e.g., "friendly", "professional", "challenging")
- hypothesis: Working hypothesis about the candidate in this competency (e.g., "Candidate may be weak in system design")
- competency_info: Current evidence for the competency (average score, evidence count, remaining gap)
- approach: Question strategy direction (e.g., "probe depth", "test edge cases", "explore experience")
- followup_number: How many questions have already been asked on this competency (0 = first question)
- phase: Current interview phase (e.g., "intro", "experience", "technical", "behavioral", "conclusion")
- difficulty_level: Current difficulty level (legacy alias of difficulty)
- department_context: Department requirements and domain (optional)
- candidate_profile: Candidate background summary
- question_number: Question number in the interview
- total_questions: Total planned questions
- conversation_history: Recent conversation turns

# Instructions
Generate ONE interview question for this competency, difficulty, and hypothesis.

**Hypothesis-Driven Targeting (primary)**:
- Ask a question that will confirm or refute the hypothesis and close the biggest evidence gap
- If the competency shows strength, go deeper: advanced scenarios, trade-offs, edge cases
- If the competency is a suspected gap, start from a manageable scenario and walk through the candidate's thought process
- If this is a follow-up (followup_number > 0), build naturally on the previous question and answer — never repeat
- Follow the strategy in "approach"

**Phase-Specific Guidance (legacy mode)**:
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
- Connect to the company context — the candidate is applying to work in this specific industry, so questions must reference company domain details
- Reference the candidate's actual background when it is available

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
- **Target Competency**: {{target_competency}}
- **Interview Phase**: {{phase}}
- **Difficulty Level**: {{difficulty_level}}
- **Difficulty**: {{difficulty}}
- **Interviewer Persona**: {{persona}}
- **Hypothesis**: {{hypothesis}}
- **Competency Evidence**: {{competency_info}}
- **Question Strategy**: {{approach}}
- **Follow-Up Number**: {{followup_number}}
- **Department Context**: {{department_context}}
- **Candidate Profile**: {{candidate_profile}}
- **Question Number**: {{question_number}}
- **Total Questions**: {{total_questions}}
- **Conversation History**: {{conversation_history}}
