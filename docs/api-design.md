# AI Interview Agent - API Design

## Overview

This document describes the API endpoints available in the AI Interview Agent system, including request/response formats, authentication, and error handling.

## API Base URL

```
http://localhost:8000
```

## API Structure

The API is organized by functionality:

- `/companies/` - Company management
- `/companies/{company_id}/interview/` - Interview operations
- `/companies/{company_id}/interview/session/` - Session management
- `/upload-document` - File upload
- `/create-knowledge-base` - Knowledge base creation
- `/health` - Health check endpoint

## Authentication

**Current State**: No authentication/authorization implemented

**Recommended Future State**:
```python
# Use FastAPI dependency injection for authentication
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Validate token
    return current_user
```

## Rate Limiting

**Current State**: Not implemented

**Recommended Future State**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
```

## Request/Response Format

All requests and responses follow JSON format.

### Standard Response Structure

**Success Response**:
```json
{
  "message": "Operation successful",
  "data": { ... }
}
```

**Error Response**:
```json
{
  "detail": "Error message"
}
```

## API Endpoints

### Companies Endpoints

#### Create Company
**POST** `/companies/`

**Request Body**:
```json
{
  "name": "String required",
  "website": "String optional",
  "description": "String optional"
}
```

**Response** (201 Created):
```json
{
  "message": "Company created",
  "company": {
    "id": 1,
    "name": "Example Company",
    "website": "https://example.com",
    "description": "Example description",
    "created_at": "2026-07-18T15:30:00Z"
  }
}
```

**Error** (400, 500):
```json
{
  "detail": "Company name is required"
}
```

#### List Companies
**GET** `/companies/`

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "name": "Company 1",
    "website": "https://company1.com",
    "description": "Description 1"
  },
  {
    "id": 2,
    "name": "Company 2",
    "website": "https://company2.com",
    "description": "Description 2"
  }
]
```

#### Get Company
**GET** `/companies/{company_id}`

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "Company 1",
  "website": "https://company1.com",
  "description": "Description 1"
}
```

**Error** (404 Not Found):
```json
{
  "detail": "Company not found"
}
```

**Error** (500 Internal Server Error):
```json
{
  "detail": "Database error"
}
```

#### Delete Company
**DELETE** `/companies/{company_id}`

**Response** (200 OK):
```json
{
  "message": "Company deleted"
}
```

**Error** (404, 500):
```json
{
  "detail": "Error message"
}
```

### Interview Session Endpoints

#### Start Interview Session
**POST** `/companies/{company_id}/interview/session`

**Request Body**:
```json
{
  "job_role": "String required"
}
```

**Response** (201 Created):
```json
{
  "session_id": "uuid-string",
  "current_phase": "intro",
  "question_number": 0,
  "total_questions": 16
}
```

**Error** (400 Bad Request):
```json
{
  "detail": "job_role is required"
}
```

**Error** (500 Internal Server Error):
```json
{
  "detail": "Database error: Session creation failed"
}
```

#### Get Interview Session Status
**GET** `/companies/{company_id}/interview/session/{session_id}`

**Response** (200 OK):
```json
{
  "session_id": "uuid-string",
  "company_id": 1,
  "job_role": "Software Engineer",
  "status": "active",
  "current_phase": "technical",
  "question_number": 3,
  "total_questions": 16,
  "final_score": null,
  "interview_complete": false
}
```

#### Get Next Question
**POST** `/companies/{company_id}/interview/session/{session_id}/next`

**Request Body**:
```json
{
  "job_role": "String required",
  "conversation_history": "String optional",
  "current_phase": "String optional",
  "question_number": "Integer optional",
  "difficulty_level": "Integer optional",
  "previous_scores": ["Array of integers optional"]
}
```

**Response** (200 OK):
```json
{
  "question": "Tell me about your experience with distributed systems...",
  "phase": "technical",
  "question_number": 3,
  "difficulty_level": 2,
  "interview_status": "in_progress"
}
```

**Error** (400 Bad Request):
```json
{
  "detail": "Session not found"
}
```

#### Submit Candidate Answer
**POST** `/companies/{company_id}/interview/answer`

**Request Body**:
```json
{
  "job_role": "String required",
  "session_id": "String required",
  "question": "String required",
  "candidate_answer": "String required",
  "conversation_history": "String optional",
  "current_phase": "String optional",
  "difficulty_level": "Integer optional",
  "question_number": "Integer optional"
}
```

**Response** (200 OK):
```json
{
  "evaluation": "**Score:** 7.5/10\n\n**Breakdown:**\n- Technical Knowledge: 7/10\n- Problem Solving: 8/10\n- Communication: 7/10\n- Overall Impression: 7/10\n\n**Strengths:**\n- Demonstrates good understanding of system design\n- Communication is clear\n\n**Areas for Growth:**\n- Could provide more specific examples\n\n**Suggested Follow-up Question:**\nTell me about the trade-offs you considered when choosing this architecture.\n\n**Overall Feedback:**\nStrong technical candidate with good communication skills.\n\n**Score:** 7.5",
  "suggested_follow_up": "Tell me about the trade-offs you considered when choosing this architecture.",
  "phase": "technical",
  "question_number": 3,
  "difficulty_level": 2,
  "interview_status": "in_progress",
  "score": 7.5
}
```

**Error** (422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "loc": ["body", "session_id"],
      "msg": "field required"
    }
  ]
}
```

**Error** (500 Internal Server Error):
```json
{
  "detail": "Error evaluating answer"
}
```

### Deprecated Interview Endpoints

The following endpoints are kept for backward compatibility but are not recommended for new development:

#### Deprecated: Company Interview (Graph-based)
**POST** `/companies/{company_id}/interview`

**Body** (deprecated):
```json
{
  "job_role": "String",
  "candidate_answer": "String",
  "question": "String",
  "company_context": "String"
}
```

**Response**:
```json
{
  "company_id": 1,
  "job_role": "Software Engineer",
  "question": "Tell me about your experience...",
  "evaluation": "Score: 7/10"
}
```

#### Deprecated: Follow-up Question
**POST** `/companies/{company_id}/interview/follow-up`

**Body** (deprecated):
```json
{
  "job_role": "String",
  "previous_question": "String",
  "previous_answer": "String"
}
```

**Response**:
```json
{
  "company_id": 1,
  "follow_up_question": "Tell me more about your approach..."
}
```

#### Deprecated: Evaluate with Follow-up
**POST** `/companies/{company_id}/interview/evaluate-with-followup`

**Body** (deprecated):
```json
{
  "job_role": "String",
  "question": "String",
  "candidate_answer": "String"
}
```

**Response**:
```json
{
  "company_id": 1,
  "job_role": "Software Engineer",
  "question": "String",
  "candidate_answer": "String",
  "evaluation": "Score: 7/10",
  "suggested_follow_up": "Follow-up question"
}
```

### Knowledge Base Endpoints

#### Upload Document
**POST** `/upload-document`

**Request**: `file: UploadFile`

**Response** (200 OK):
```json
{
  "message": "Document uploaded",
  "filename": "company.pdf"
}
```

**Error** (500):
```json
{
  "error": "Error uploading document"
}
```

#### Create Knowledge Base
**POST** `/create-knowledge-base`

**Response** (200 OK):
```json
{
  "message": "Knowledge base created",
  "chunks": 150
}
```

**Error** (500):
```json
{
  "error": "Error creating knowledge base"
}
```

### Health Check Endpoints

#### Health Check
**GET** `/health` | **POST** `/health`

**Response** (200 OK):
```json
{
  "status": "✅ API is working",
  "message": "You can now access the API from your HTML file",
  "timestamp": "2026-07-18T15:30:00",
  "cors": "✅ CORS enabled"
}
```

**Error** (500):
```json
{
  "detail": "Error message"
}
```

## Request Models (Pydantic Schemas)

### SessionStartRequest
```python
from pydantic import BaseModel

class SessionStartRequest(BaseModel):
    job_role: str
```

### AnswerRequest
```python
class AnswerRequest(BaseModel):
    job_role: str
    session_id: str
    question: str
    candidate_answer: str
    conversation_history: Optional[str] = ""
    current_phase: Optional[str] = None
    difficulty_level: Optional[int] = None
    question_number: Optional[int] = None
```

### CompanyCreate
```python
class CompanyCreate(BaseModel):
    name: str
    website: str | None = None
    description: str | None = None
```

## Response Models

### InterviewSessionResponse
```python
from pydantic import BaseModel

class InterviewSessionResponse(BaseModel):
    session_id: str
    current_phase: str
    question_number: int
    total_questions: int
    company_id: int
    job_role: str
    status: str
```

### InterviewQuestionResponse
```python
class InterviewQuestionResponse(BaseModel):
    question: str
    phase: str
    question_number: int
    difficulty_level: int
    interview_status: str
```

### EvaluationResponse
```python
class EvaluationResponse(BaseModel):
    evaluation: str
    suggested_follow_up: str
    phase: str
    question_number: int
    difficulty_level: int
    interview_status: str
    score: float
```

## CORS Configuration

- **Allow Origins**: `*` (all origins)
- **Allow Credentials**: `true`
- **Allow Methods**: `*` (all methods)
- **Allow Headers**: `*` (all headers)

**Middleware Order** (CRITICAL):
1. CORSMiddleware - Must be FIRST
2. NgrokMiddleware - Custom middleware for ngrok headers

## Error Handling Rules

### HTTP Status Codes

- **200 OK**: Successful operation
- **201 Created**: Resource created
- **400 Bad Request**: Invalid request data
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

### Error Response Format

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=400,
    detail="Validation error message"
)
```

### Structured Error Responses

```python
{
  "detail": "Error message",
  "code": "ERROR_CODE",  # Optional error code
  "metadata": {  # Optional contextual info
    "field": "some_field",
    "value": "bad_value"
  }
}
```

## Validation

### Request Validation
- Use Pydantic models for all requests
- Enable validation on all endpoints
- Provide clear error messages for validation failures

### Response Formatting
- Return consistent response structures
- Use `404` for missing resources
- Use `422` for validation errors
- Use `500` for server errors only

## Layering Rules

### API Layer Responsibilities
✅ **DO**:
- Validate request using Pydantic schemas
- Handle HTTP details (headers, status codes)
- Call service layer for business logic
- Format response data
- Log significant events

❌ **DON'T**:
- Implement business logic
- Directly access database
- Invoke LLM operations
- Parse business rules
- Handle complex workflows

### Service Layer Interface
```python
# Service methods should be clean and focused
class InterviewService:
    async def start_session(
        self,
        company_id: int,
        job_role: str
    ) -> InterviewSession:
        """Start a new interview session"""
        pass
    
    async def get_next_question(
        self,
        company_id: int,
        session_id: str
    ) -> InterviewQuestion:
        """Get the next interview question"""
        pass
    
    async def evaluate_answer(
        self,
        company_id: int,
        data: AnswerData
    ) -> Evaluation:
        """Evaluate candidate answer and generate feedback"""
        pass
```

## Documentation

All endpoints should include:
- Purpose description
- Request parameters (required/optional)
- Request body schema
- Response schema
- Error cases
- Examples

**Example**:
```python
@router.post("/companies/{company_id}/interview/session")
async def start_interview_session(
    company_id: int,
    request: SessionStartRequest,
    current_phase: str = "intro",
):
    """
    Create a new interview session.
    
    Start a new interview session for a job role.
    The session will initialize in the specified phase
    (default: intro).
    
    Path Parameters:
        company_id (int): Company identifier
    
    Body:
        job_role (str): Target job role for the interview
    
    Query Parameters:
        current_phase (str): Interview phase to start in
            Valid values: intro, experience, technical, 
            behavioral, conclusion
            Default: "intro"
    
    Returns:
        InterviewSessionResponse: Session details including
            session_id, current_phase, question_number,
            total_questions
    
    Raises:
        HTTPException (400): If job_role is missing
        HTTPException (500): If session creation fails
    """
    pass