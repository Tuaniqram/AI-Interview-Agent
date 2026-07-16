import os
import shutil
import logging

from fastapi import APIRouter, UploadFile, File

from app.rag.loader import load_pdf
from app.rag.splitter import split_documents
from app.rag.pinecone_store import store_company_knowledge
from app.config.database import get_supabase


router = APIRouter(
    prefix="/companies",
    tags=["Knowledge"]
)


logger = logging.getLogger(__name__)


UPLOAD_DIR = "documents"



@router.post("/{company_id}/knowledge")
async def upload_knowledge(

    company_id:int,

    file:UploadFile = File(...)

):

    os.makedirs(
        UPLOAD_DIR,
        exist_ok=True
    )


    filepath = f"{UPLOAD_DIR}/{file.filename}"


    with open(filepath,"wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )



    # 1. Load PDF

    documents = load_pdf(
        filepath
    )


    # 2. Split

    chunks = split_documents(
        documents
    )


    # 3. Store Pinecone

    store_company_knowledge(
        chunks,
        company_id
    )



    # 4. Save metadata Supabase

    db = get_supabase()


    db.table(
        "company_documents"
    ).insert({

        "company_id":company_id,

        "filename":file.filename,

        "document_type":"pdf",

        "pinecone_namespace":
            f"company_{company_id}"

    }).execute()



    return {

        "message":
        "Knowledge uploaded",

        "company_id":
        company_id,

        "chunks":
        len(chunks)

    }