# AI Interview Agent

An intelligent interview system that leverages LLMs and RAG (Retrieval-Augmented Generation) to conduct technical interviews based on company knowledge bases.

## Features

- **Document Upload & RAG**: Upload company documents to create a knowledge base
- **Intelligent Interviewer**: Generates interview questions based on company requirements
- **Answer Evaluation**: Evaluates candidate responses with scoring and feedback
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

#### 4. Run Interview Workflow
```
POST /interview
```
Execute the full interview workflow:
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
  "question": "Generated interview question",
  "company_context": "Relevant company information",
  "feedback": "Evaluation and feedback"
}
```

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI application
│   ├── models/
│   │   └── llm.py          # LLM configuration
│   ├── agents/
│   │   ├── retriever.py    # Retrieval agent
│   │   ├── interviewer.py  # Interview generation agent
│   │   └── evaluator.py    # Answer evaluation agent
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

## Architecture

### Workflow Stages

1. **Retrieval**: Query the vector database for relevant company context
2. **Interview**: Generate targeted interview questions based on job role and company requirements
3. **Evaluation**: Assess candidate answers with scoring and constructive feedback

### Technologies Used

- **FastAPI**: REST API framework
- **LangChain**: LLM integration and RAG framework
- **LangGraph**: Agent workflow orchestration
- **FAISS**: Vector similarity search
- **HuggingFace**: Embeddings (all-MiniLM-L6-v2)
- **OpenRouter**: LLM API provider

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

## License

MIT
