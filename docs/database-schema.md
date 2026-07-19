# AI Interview Agent - Database Schema

## Overview

This document describes the database structure for the AI Interview Agent system. The database is managed via Supabase (PostgreSQL) and contains 4 main tables for managing companies, interview sessions, messages, and evaluations.

## Tables Overview

1. **companies** - Company information and profiles
2. **company_documents** - Company documentation (PDFs) stored in Pinecone
3. **interview_sessions** - Interview session management
4. **interview_messages** - Individual interview messages and questions
5. **interview_evaluations** - Detailed evaluations per answer
6. **user_progress** - Candidate performance tracking

## Table Definitions

### companies Table

**Purpose**: Store company information for interview contexts

**Schema**:
```sql
CREATE TABLE public.companies (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name text NOT NULL,
  website text,
  description text,
  created_at timestamp with time zone DEFAULT now()
);
```

**Fields**:
- `id`: Primary key (auto-incremented bigint)
- `name`: Company name (required, max length unlimited)
- `website`: Company website URL (optional)
- `description`: Company description (optional)
- `created_at`: Timestamp of record creation

**Indexes**:
- Primary key constraint on `id`

**Example Data**:
```json
{
  "id": 1,
  "name": "Tech Corp",
  "website": "https://techcorp.com",
  "description": "Leading technology company",
  "created_at": "2026-07-18T15:30:00Z"
}
```

### company_documents Table

**Purpose**: Track company documents uploaded to the system

**Schema**:
```sql
CREATE TABLE public.company_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id bigint REFERENCES public.companies(id) ON DELETE CASCADE,
  filename text NOT NULL,
  document_type text NOT NULL DEFAULT 'pdf',
  pinecone_namespace text NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);
```

**Fields**:
- `id`: UUID primary key (auto-generated)
- `company_id`: Foreign key to companies table
- `filename`: Original filename of uploaded document (required)
- `document_type`: Type of document (required, defaults to 'pdf')
- `pinecone_namespace`: Namespace for Pinecone vector storage (required)
- `created_at`: Timestamp of file upload

**Indexes**:
- Primary key constraint on `id`
- Foreign key constraint to `companies(id)`
- Index on `company_id` for fast joins

**Example Data**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "company_id": 1,
  "filename": "company-research.pdf",
  "document_type": "pdf",
  "pinecone_namespace": "company_1_context",
  "created_at": "2026-07-18T15:30:00Z"
}
```

### interview_sessions Table

**Purpose**: Manage interview sessions with state tracking

**Schema**:
```sql
CREATE TABLE public.interview_sessions (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  company_id bigint REFERENCES public.companies(id) ON DELETE CASCADE,
  candidate_id text,
  job_role text NOT NULL,
  interview_type text DEFAULT 'company',
  status text DEFAULT 'active',
  current_phase text DEFAULT 'intro',
  current_question_number integer DEFAULT 0,
  total_questions integer,
  started_at timestamp with time zone DEFAULT now(),
  ended_at timestamp with time zone,
  final_score numeric CHECK (score >= 0::numeric AND score <= 10::numeric),
  final_feedback text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);
```

**Fields**:
- `id`: UUID primary key (auto-generated)
- `company_id`: Foreign key to companies table
- `candidate_id`: Candidate identifier (optional, text format)
- `job_role`: Target job role for interview (required)
- `interview_type`: Type of interview (e.g., 'company', 'personal')
- `status`: Session status (e.g., 'active', 'completed')
- `current_phase`: Current interview phase (e.g., 'intro', 'technical', 'conclusion')
- `current_question_number`: Current question number (starting from 0)
- `total_questions`: Total questions to complete the interview
- `started_at`: Timestamp when interview started
- `ended_at`: Timestamp when interview ended (null until completion)
- `final_score`: Final score between 0 and 10
- `final_feedback`: Summary feedback (optional)
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

**Insertion Logic**:
The `total_questions` should be calculated dynamically:
```python
total_questions = (
    intro_count + experience_count + technical_count + 
    behavioral_count + conclusion_count
)
```

**Constants**:
- `total_questions` = 2 (intro) + 3 (experience) + 5 (technical) + 3 (behavioral) + 10 (conclusion) = **23**
- Phases: `intro`, `experience`, `technical`, `behavioral`, `conclusion`

**Example Data**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "company_id": 1,
  "candidate_id": "candidate_123",
  "job_role": "Software Engineer",
  "interview_type": "company",
  "status": "active",
  "current_phase": "intro",
  "current_question_number": 0,
  "total_questions": 23,
  "started_at": "2026-07-18T15:30:00Z",
  "ended_at": null,
  "final_score": null,
  "final_feedback": null,
  "created_at": "2026-07-18T15:30:00Z",
  "updated_at": "2026-07-18T15:30:00Z"
}
```

### interview_messages Table

**Purpose**: Store all messages exchanged during interview sessions

**Schema**:
```sql
CREATE TABLE public.interview_messages (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id uuid REFERENCES public.interview_sessions(id) ON DELETE CASCADE,
  role text NOT NULL,
  message_type text NOT NULL,
  content text NOT NULL,
  question_number integer DEFAULT 0,
  phase text,
  score numeric,
  follow_up_question text,
  evaluated_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now()
);
```

**Fields**:
- `id`: UUID primary key (auto-generated)
- `session_id`: Foreign key to interview_sessions
- `role`: Role of message sender ('candidate' or 'interviewer')
- `message_type`: Type of message (e.g., question, answer)
- `content`: Message text content
- `question_number`: Sequence number of the question (starts from 0)
- `phase`: Interview phase when message occurred
- `score`: Score assigned if the message was evaluated
- `follow_up_question`: Generated follow-up question (if applicable)
- `evaluated_at`: Timestamp when evaluation occurred
- `created_at`: Record creation timestamp

**Indexes**:
- Primary key constraint on `id`
- Foreign key constraint to `interview_sessions(id)`
- Composite index on `(session_id, created_at)` for querying conversation history
- Index on `session_id` for fast lookups

**Important**:
- `role` should be 'candidate' for answers and 'interviewer' for questions
- `message_type` should match `question_number`
- Questions and answers should be inserted in sequence

**Example Data**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "session_id": "550e8400-e29b-41d4-a716-446655440001",
  "role": "interviewer",
  "message_type": "Tell me about your background and your career experience with software engineering.",
  "content": "Tell me about your background and your career experience with software engineering.",
  "question_number": 0,
  "phase": "intro",
  "score": null,
  "follow_up_question": null,
  "evaluated_at": null,
  "created_at": "2026-07-18T15:32:00Z"
}
```

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "session_id": "550e8400-e29b-41d4-a716-446655440001",
  "role": "candidate",
  "message_type": "Tell me about your background and your career experience with software engineering.",
  "content": "I have 5 years of experience in software engineering...",
  "question_number": 0,
  "phase": "intro",
  "score": 8,
  "follow_up_question": "Can you give me a specific example of a challenging project you worked on?",
  "evaluated_at": "2026-07-18T15:33:00Z",
  "created_at": "2026-07-18T15:32:30Z"
}
```

### interview_evaluations Table

**Purpose**: Detailed evaluation data for each candidate answer

**Schema**:
```sql
CREATE TABLE public.interview_evaluations (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id uuid REFERENCES public.interview_sessions(id) ON DELETE CASCADE,
  message_id uuid REFERENCES public.interview_messages(id) ON DELETE CASCADE,
  score numeric CHECK (score >= 0::numeric AND score <= 10::numeric),
  technical_score numeric,
  communication_score numeric,
  strengths text,
  weaknesses text,
  feedback_detail text,
  evaluated_at timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now()
);
```

**Fields**:
- `id`: UUID primary key (auto-generated)
- `session_id`: Foreign key to interview_sessions
- `message_id`: Foreign key to interview_messages (link to the specific answer)
- `score`: Overall score (0-10)
- `technical_score`: Technical knowledge score (0-10)
- `communication_score`: Communication skills score (0-10)
- `strengths`: Identified strengths from the answer
- `weaknesses`: Identified areas for improvement
- `feedback_detail`: Full evaluation feedback
- `evaluated_at`: Evaluation timestamp
- `created_at`: Record creation timestamp

**Indexes**:
- Primary key constraint on `id`
- Foreign key constraints to `interview_sessions(id)` and `interview_messages(id)`
- Index on `session_id` for looking up all evaluations for a session

**Relationships**:
- One-to-one with interview_messages
- One-to-many with interview_sessions

**Example Data**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440004",
  "session_id": "550e8400-e29b-41d4-a716-446655440001",
  "message_id": "550e8400-e29b-41d4-a716-446655440003",
  "score": 7.5,
  "technical_score": 7,
  "communication_score": 8,
  "strengths": "Good technical knowledge, clear communication",
  "weaknesses": "Could provide more specific examples",
  "feedback_detail": "**Score:** 7.5/10\n\n**Breakdown:**\n- Technical Knowledge: 7/10\n- Problem Solving: 8/10\n- Communication: 7/10\n\n**Strengths:**\n- Demonstrates good understanding of system design\n- Communication is clear\n\n**Areas for Growth:**\n- Could provide more specific examples\n\n**Overall Feedback:**\nStrong technical candidate with good communication skills.",
  "evaluated_at": "2026-07-18T15:33:00Z",
  "created_at": "2026-07-18T15:33:00Z"
}
```

### user_progress Table

**Purpose**: Track individual candidate performance over time

**Schema**:
```sql
CREATE TABLE public.user_progress (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id uuid REFERENCES public.interview_sessions(id) ON DELETE CASCADE,
  candidate_identifier text,
  average_score numeric,
  total_questions_answered integer,
  questions_correct integer,
  strengths_improvement_count integer,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);
```

**Fields**:
- `id`: UUID primary key (auto-generated)
- `session_id`: Foreign key to interview_sessions
- `candidate_identifier`: Unique candidate identifier (e.g., email, ID)
- `average_score`: Average score across all questions
- `total_questions_answered`: Count of answered questions
- `questions_correct`: Count of questions with score > 7 (optional metric)
- `strengths_improvement_count`: Count of identified areas for growth
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

**Indexes**:
- Primary key constraint on `id`
- Foreign key constraint to `interview_sessions(id)`

**Usage**:
- Not currently used in the system
- Can be used for tracking candidate performance across multiple sessions

## Relationships

```
companies
    │
    ├─ has many ─> company_documents
    │
    └─ has many ─> interview_sessions
                      │
                      ├─ has many ─> interview_messages
                      │               │
                      │               └─ has one ─> interview_evaluations
                      │
                      └─ may have one ─> user_progress
```

## Business Rules

### Question Numbering
- Starts at `0` (not `1`)
- Increments after each question-answer cycle
- Total questions across all phases: **23**
  - Intro: 2
  - Experience: 3
  - Technical: 5 (adjustable based on performance)
  - Behavioral: 3
  - Conclusion: 10

### Phase Transitions
- **Intro** → **Experience** (after 2 questions)
- **Experience** → **Technical** (after 5 questions)
- **Technical** → **Technical** (weak performance)
- **Technical** → **Conclusion** (strong performance or question 8)
- **Behavioral** → **Conclusion** (after 3 questions)
- **Conclusion** → **Completed** (automatic completion)

### Difficulty Adaptation
Based on score:
- Score > 7.0: `difficulty_level = 3` (hard)
- Score > 5.0: `difficulty_level = 2` (medium)
- Score ≤ 5.0: `difficulty_level = 1` (easy)

### Interview Completion
- Automatically completes when:
  - `current_phase == "conclusion"`
  - `current_question_number >= total_questions`
  - `status == "completed"`

## Query Patterns

### Get Active Sessions
```sql
SELECT * FROM interview_sessions
WHERE status = 'active'
ORDER BY created_at DESC;
```

### Get Interview Conversation
```sql
SELECT 
    id, role, message_type, content, score, phase, created_at
FROM interview_messages
WHERE session_id = 'session_uuid'
ORDER BY created_at;
```

### Get Final Evaluation
```sql
SELECT eval.*, session.final_feedback
FROM interview_evaluations eval
JOIN interview_sessions session ON eval.session_id = session.id
WHERE session.id = 'session_uuid';
```

### Get Candidate Progress
```sql
SELECT 
    session_id,
    candidate_identifier,
    AVG(score) as average_score,
    COUNT(*) as total_questions_done
FROM interview_messages
WHERE role = 'candidate' AND session_id = 'session_uuid'
GROUP BY session_id, candidate_identifier;
```

## Development Rules

1. **Always use UUIDs** for primary keys (auto-generated)
2. **Use foreign keys** with CASCADE delete when appropriate
3. **Timestamp all records** with `created_at` and `updated_at`
4. **Use indexes** on foreign keys and frequently queried columns
5. **Validate scores** between 0-10 when inserting
6. **Maintain sequence** of questions (0, 1, 2, 3...)
7. **Track all messages** regardless of evaluation
8. **Never delete** interview sessions or messages (archive instead)

## Migration Strategy

When adding new fields:
1. Use `ALTER TABLE` with `ADD COLUMN`
2. Set default values for existing records
3. Add indexes if the field is frequently queried
4. Document the change in this schema file

When refactoring:
1. Create new tables to maintain backward compatibility
2. Add migration scripts to `scripts/migrations/`
3. Test migrations in staging environment
4. Document breaking changes

## Supabase Client Usage

**Singleton Access**:
```python
from app.config.database import get_supabase

supabase = get_supabase()
```

**Common Operations**:
```python
# Insert
response = supabase.table("interview_sessions").insert({
    "id": str(uuid.uuid4()),
    "company_id": company_id,
    "job_role": job_role,
    "status": "active"
}).execute()

# Select
response = supabase.table("interview_sessions").select("*").eq("id", session_id).execute()

# Update
response = supabase.table("interview_sessions").update({
    "current_question_number": new_number,
    "status": "completed"
}).eq("id", session_id).execute()

# Join
response = (supabase.table("interview_messages")
    .select("id, role, content")
    .eq("session_id", session_id)
    .execute())
```

## Scalability Considerations

1. **Indexing**: Ensure indexes on frequently queried columns
2. **Batch Operations**: Use Supabase batch inserts for efficiency
3. **Pagination**: Implement pagination for large result sets
4. **Connection Pooling**: Use Supabase's connection pooling
5. **Read Replicas**: Consider read replicas for read-heavy workloads

## Security Considerations

1. **Row Level Security**: Enable RLS for production
2. **Authentication**: Implement user authentication
3. **Authorization**: Restrict access to `company_id` fields
4. **Input Validation**: Validate all data before insertion
5. **Audit Logging**: Log sensitive operations