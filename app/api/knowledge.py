import os
import shutil
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.config.database import get_supabase


router = APIRouter(
    prefix="/companies",
    tags=["Knowledge"]
)


logger = logging.getLogger(__name__)


UPLOAD_DIR = "documents"

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md"}


@router.get("/{company_id}/knowledge")
def list_knowledge(company_id: int):
    """List all uploaded documents for a company."""
    try:
        db = get_supabase()
        result = (
            db.table("company_documents")
            .select("*")
            .eq("company_id", company_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error(f"List knowledge error: {str(e)}")
        return []


@router.delete("/{company_id}/knowledge/{doc_id}")
def delete_knowledge(company_id: int, doc_id: str):
    """Delete a document: Supabase metadata + disk file + Pinecone vectors."""
    try:
        db = get_supabase()

        # Fetch the record first so we know the filename
        result = (
            db.table("company_documents")
            .select("filename")
            .eq("id", doc_id)
            .eq("company_id", company_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        filename = result.data[0].get("filename")

        # 1. Delete vectors from Pinecone (best-effort)
        try:
            from app.rag.pinecone_store import delete_company_knowledge
            delete_company_knowledge(company_id, doc_id)
        except Exception as e:
            logger.warning(f"Pinecone delete failed (continuing): {e}")

        # 2. Delete from Supabase
        db.table("company_documents").delete().eq("id", doc_id).eq("company_id", company_id).execute()

        # 3. Delete file from disk (best-effort)
        if filename:
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted file from disk: {filepath}")

        return {"message": "Document deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete knowledge error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{company_id}/knowledge")
async def upload_knowledge(
    company_id: int,
    file: UploadFile = File(...)
):
    # Validate file extension
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Step 1: Save file to disk
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filepath = f"{UPLOAD_DIR}/{file.filename}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logger.info(f"File saved to disk: {filepath}")

    # Step 2: Insert metadata into Supabase FIRST to get the doc_id
    doc_id = None
    try:
        db = get_supabase()
        insert_result = db.table("company_documents").insert({
            "company_id": company_id,
            "filename": file.filename,
            "document_type": ext.lstrip(".").lower() or "pdf",
            "pinecone_namespace": f"company_{company_id}"
        }).execute()
        doc_id = insert_result.data[0]["id"] if insert_result.data else None
        logger.info(f"Metadata saved to Supabase: doc_id={doc_id}")
    except Exception as e:
        logger.error(f"Failed to save metadata to Supabase: {e}")
        raise HTTPException(status_code=500, detail=f"File saved but metadata save failed: {e}")

    # Step 3-4: RAG pipeline (best-effort, tags vectors with doc_id)
    chunks_count = 0
    rag_error = None
    try:
        from app.rag.loader import load_pdf
        from app.rag.splitter import split_documents
        from app.rag.pinecone_store import store_company_knowledge

        documents = load_pdf(filepath)
        chunks = split_documents(documents)
        store_company_knowledge(chunks, company_id, doc_id=doc_id)
        chunks_count = len(chunks)
        logger.info(f"RAG pipeline completed: {chunks_count} chunks stored (doc_id={doc_id})")
    except Exception as e:
        rag_error = str(e)
        logger.warning(f"RAG pipeline failed (file still saved): {e}")

    response = {
        "message": "Document uploaded",
        "company_id": company_id,
        "filename": file.filename,
        "doc_id": doc_id,
    }

    if chunks_count > 0:
        response["chunks"] = chunks_count

    if rag_error:
        response["warning"] = f"File saved but RAG processing failed: {rag_error}"

    return response
