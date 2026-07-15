# AI Interview Agent

An intelligent interview system that leverages LLMs and RAG (Retrieval-Augmented Generation) to conduct technical interviews based on company knowledge bases. The interviewer generates **natural, conversational questions** just like a real human interviewer would ask.

## Features

- **Document Upload & RAG**: Upload company documents to create a knowledge base
- **Human-Like Interviewer**: Generates natural, conversational questions - not formal or scripted
- **Real Interview Flow**: Questions sound like something an actual interviewer would ask
- **Answer Evaluation**: Evaluates candidate responses with honest, constructive feedback
- **Follow-Up Questions**: Natural follow-up questions to dig deeper into candidate's experience
- **LangGraph Workflow**: Orchestrated multi-agent workflow for interview management
- **FastAPI REST API**: Easy-to-use REST endpoints for integration

## Setup

### 1. Clone and Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Add your OpenRouter API key:

```
OPENROUTER_API_KEY=your_api_key_here
```

### 3. Create Required Directories

```bash
mkdir -p documents vector_db
```

## Usage

### Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### 1. Upload Document
```
POST /upload-document
```
Upload an HR document (PDF):
```json
{
  "file": "company.pdf"
}
```

#### 2. Create Knowledge Base
```
POST /create-knowledge-base
```
Create vector embeddings from uploaded documents:
```json
{}
```

Response:
```json
{
  "message": "Knowledge base created",
  "chunks": 42
}
```

#### 3. Ask Question (RAG)
```
POST /ask
```
Query the knowledge base:
```json
{
  "question": "What are the main requirements for a senior developer?"
}
```

Response:
```json
{
  "question": "What are the main requirements for a senior developer?",
  "context": "...",
  "answer": "..."
}
```

#### 4. Run Full Interview Workflow
```
POST /interview
```
Execute the complete interview workflow with natural question generation and evaluation:
```json
{
  "job_role": "Senior Backend Engineer",
  "candidate_answer": "I have 5 years of experience with Python and microservices..."
}
```

Response:
```json
{
  "job_role": "Senior Backend Engineer",
  "question": "Can you walk me through a project where you had to make a tough architectural decision?",
  "company_context": "Key Requirements for Senior Backend Engineer: ...",
  "candidate_answer": "I have 5 years of experience...",
  "feedback": "Score: 7/10. Strengths: You showed relevant experience... Follow-up: What was the biggest challenge...",
  "interview_complete": true
}
```

#### 5. Evaluate Answer + Get Follow-Up Question
```
POST /interview/evaluate-with-followup
```
Evaluate a candidate's answer and get a natural follow-up question:
```json
{
  "job_role": "Backend Developer",
  "question": "Tell me about a time you had to debug a complex performance issue.",
  "candidate_answer": "I once had to optimize a slow API endpoint...",
  "company_context": "Backend requirements: MySQL, Docker, REST APIs"
}
```

Response:
```json
{
  "job_role": "Backend Developer",
  "question": "Tell me about a time you had to debug a complex performance issue.",
  "candidate_answer": "I once had to optimize a slow API endpoint...",
  "evaluation": "Score: 8/10. You clearly have hands-on experience...",
  "suggested_follow_up": "What tools did you use to identify the performance bottleneck?"
}
```

#### 6. Generate Follow-Up Question
```
POST /interview/follow-up
```
Generate a natural follow-up question based on previous exchange:
```json
{
  "job_role": "Backend Developer",
  "previous_question": "Tell me about a time you had to debug a complex performance issue.",
  "previous_answer": "I used Laravel Debugbar to identify N+1 queries...",
  "company_context": "Backend requirements"
}
```

Response:
```json
{
  "job_role": "Backend Developer",
  "previous_question": "Tell me about a time you had to debug a complex performance issue.",
  "previous_answer": "I used Laravel Debugbar to identify N+1 queries...",
  "follow_up_question": "How did you implement caching to prevent those queries in the future?"
}
```

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI application with all endpoints
│   ├── models/
│   │   └── llm.py          # LLM configuration
│   ├── agents/
│   │   ├── retriever.py    # Retrieval agent - gets company context
│   │   ├── interviewer.py  # Interview agent - generates natural questions
│   │   └── evaluator.py    # Evaluation agent - provides human-like feedback
│   ├── graph/
│   │   └── workflow.py     # LangGraph workflow orchestration
│   └── rag/
│       ├── loader.py       # PDF document loader
│       ├── embedding.py    # Document splitting & chunking
│       ├── vectorstore.py  # Vector database management
│       └── retriever.py    # Similarity search & retrieval
├── documents/              # PDF documents storage
├── vector_db/             # FAISS vector database
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## How the Interview System Works

### Interview Generation
1. **Retrieval Phase**: System retrieves relevant company requirements based on job role
2. **Question Generation**: AI interviewer generates a **natural, conversational question** - not a formal list
3. **Answer Collection**: Candidate provides their answer
4. **Evaluation**: AI evaluator provides honest, constructive feedback like a real interviewer would

### Key Differences from Formal Systems
- ✅ Questions sound natural: "Can you walk me through a project where you had to make a tough call?"
- ❌ NOT formal: "Describe in 5 bullet points..."
- ✅ Follow-ups dig deeper: "What was the biggest challenge you faced?"
- ❌ NOT scripted lists or definitions
- ✅ Feedback is conversational: "Your answer shows solid experience, but could be more specific about..."
- ❌ NOT robotic scoring

## Technologies Used

- **FastAPI**: REST API framework
- **LangChain**: LLM integration and RAG framework
- **LangGraph**: Agent workflow orchestration
- **FAISS**: Vector similarity search
- **HuggingFace**: Embeddings (all-MiniLM-L6-v2)
- **OpenRouter**: LLM API provider (supports multiple models)

## Error Handling

The system includes comprehensive error handling with logging:
- Missing environment variables
- File not found errors
- API failures
- Invalid input validation
- State validation in workflow steps

Check logs for detailed error messages and debugging information.

## Development

### Logging

All modules include logging for debugging:
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Message")
logger.error("Error message")
```

### Adding Custom Agents

Create a new agent file in `app/agents/`:
```python
import logging
logger = logging.getLogger(__name__)

def custom_agent(state):
    try:
        # Your agent logic
        return state
    except Exception as e:
        logger.error(f"Error in custom_agent: {str(e)}")
        return state
```

Add to workflow in `app/graph/workflow.py`

## Troubleshooting

### "OPENROUTER_API_KEY not set"
Ensure `.env` file exists with a valid API key

### "Vector database not found"
Run `/create-knowledge-base` endpoint first with a PDF in `documents/` folder

### "No documents found"
Ensure a PDF file is in the `documents/` folder before creating the knowledge base

### Questions still sound formal
Make sure you're using the latest version. The system uses detailed prompts to ensure conversational tone.

## Example Usage Flow

```bash
# 1. Upload company document
curl -X POST "http://localhost:8000/upload-document" \
  -F "file=@company_guidelines.pdf"

# 2. Create knowledge base
curl -X POST "http://localhost:8000/create-knowledge-base"

# 3. Run interview
curl -X POST "http://localhost:8000/interview" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Backend Developer",
    "candidate_answer": "I have experience with Laravel API development"
  }'

# 4. Get follow-up evaluation
curl -X POST "http://localhost:8000/interview/evaluate-with-followup" \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": "Backend Developer",
    "question": "Tell me about optimizing a slow API...",
    "candidate_answer": "I used eager loading...",
    "company_context": "Requirements..."
  }'
```

## License

MIT
