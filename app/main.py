from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os

import logging
from app.api.company import router as company_router
from app.api.knowledge import router as knowledge_router
from app.api.general import router as general_router
from app.api.interview import router as interview_router
from app.rag.loader import load_pdf
from app.rag.embedding import split_documents
from app.rag.vectorstore import create_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(
    company_router,
)
app.include_router(
    knowledge_router
)

app.include_router(
    general_router
)

app.include_router(
    interview_router
)
# ✅ CORS Configuration - Must be FIRST middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ✅ Custom middleware to handle ngrok-specific headers
from starlette.middleware.base import BaseHTTPMiddleware

class NgrokMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Allow ngrok to bypass browser warning
        response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "true"
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

app.add_middleware(NgrokMiddleware)


@app.get("/")
def home():

    return {
        "status":"AI Interview Agent Running"
    }


# ✅ Test endpoint for CORS & connectivity (MUST support GET AND POST)
@app.get("/health")
@app.post("/health")
def health_check():
    """Test endpoint to verify CORS and API connectivity"""
    return {
        "status": "✅ API is working",
        "message": "You can now access the API from your HTML file",
        "timestamp": str(__import__('datetime').datetime.now()),
        "cors": "✅ CORS enabled"
    }


@app.options("/health")
async def health_options():
    """Handle CORS preflight for health endpoint"""
    return {"status": "ok"}


@app.options("/{full_path:path}")
async def preflight(full_path: str):
    """Handle CORS preflight requests"""
    return {"status": "ok"}


# Upload HR document

@app.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...)
):
    try:
        os.makedirs("documents", exist_ok=True)
        file_path = f"documents/{file.filename}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Document uploaded: {file.filename}")
        return {
            "message": "Document uploaded",
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        return {"error": str(e)}, 500



# Create RAG database

@app.post("/create-knowledge-base")
def create_knowledge_base():
    try:
        documents = load_pdf("documents/company.pdf")
        chunks = split_documents(documents)
        create_database(chunks)

        logger.info(f"Knowledge base created with {len(chunks)} chunks")
        return {
            "message": "Knowledge base created",
            "chunks": len(chunks)
        }
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}")
        return {"error": str(e)}, 500



# Test RAG
