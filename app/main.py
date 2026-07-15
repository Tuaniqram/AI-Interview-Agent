from fastapi import FastAPI, UploadFile, File
import shutil
import os
import logging

from app.rag.loader import load_pdf
from app.rag.embedding import split_documents
from app.rag.vectorstore import create_database
from app.models.llm import llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/")
def home():

    return {
        "status":"AI Interview Agent Running"
    }



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

@app.post("/ask")
def ask_company(data: dict):
    try:
        question = data.get("question", "")
        if not question:
            return {"error": "Question is required"}, 400

        from langchain_community.vectorstores import FAISS
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        db = FAISS.load_local(
            "vector_db",
            embeddings,
            allow_dangerous_deserialization=True
        )

        docs = db.similarity_search(question, k=3)

        context = "\n".join(doc.page_content for doc in docs)

        prompt = f"""
You are an HR interview assistant.

Use this company information:

{context}

Question:

{question}

Answer based only on company information.
"""

        response = llm.invoke(prompt)

        return {
            "question": question,
            "context": context,
            "answer": response.content
        }
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        return {"error": str(e)}, 500


from app.graph.workflow import graph


@app.post("/interview")
def interview(data: dict):
    try:
        if not data.get("job_role"):
            return {"error": "job_role is required"}, 400

        result = graph.invoke(data)
        logger.info("Interview workflow completed")
        return result

    except Exception as e:
        logger.error(f"Error in interview workflow: {str(e)}")
        return {"error": str(e)}, 500