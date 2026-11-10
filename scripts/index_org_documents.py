"""Re-index an organization's knowledge documents into Pinecone.

The uploads for these docs were registered in the DB but their vectors never
reached Pinecone (the source PDFs were missing from documents/ when the
background task ran). This script regenerates the demo PDFs, loads/splits
them, and stores the chunks under the EXISTING doc_ids so the DB rows and the
organization's Pinecone namespace stay consistent.

Usage:
    python scripts/index_org_documents.py <org_id>
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from seed_org_documents import GENERATORS  # noqa: E402

from app.database.session import get_session_factory  # noqa: E402
from app.models.db import OrganizationDocument  # noqa: E402
from app.rag.loader import load_pdf  # noqa: E402
from app.rag.pinecone_store import (  # noqa: E402
    get_org_retriever,
    org_namespace,
    store_org_knowledge,
)
from app.rag.splitter import split_documents  # noqa: E402

OUTPUT_DIR = Path("documents")


async def index_org(org_id: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    namespace = org_namespace(org_id)

    async with get_session_factory()() as db:
        rows = (
            await db.execute(
                select(OrganizationDocument).where(
                    OrganizationDocument.org_id == org_id,
                    OrganizationDocument.pinecone_namespace == namespace,
                )
            )
        ).scalars().all()

    if not rows:
        print(f"No doc rows for organization {org_id} (namespace {namespace})")
        return

    print(f"Indexing {len(rows)} doc(s) for organization {org_id} -> {namespace}\n")
    for doc in rows:
        gen = GENERATORS.get(doc.filename)
        pdf_path = OUTPUT_DIR / doc.filename
        if gen is not None:
            pdf = gen()
            pdf.output(str(pdf_path))
            print(f"  regenerated {doc.filename} ({pdf_path.stat().st_size / 1024:.1f} KB)")
        elif pdf_path.exists():
            print(f"  reusing existing file {doc.filename}")
        else:
            print(f"  SKIP {doc.filename}: no generator and file missing from documents/")
            continue

        try:
            documents = load_pdf(str(pdf_path))
            chunks = split_documents(documents)
            if not chunks:
                print(f"  SKIP {doc.filename}: 0 chunks")
                continue
            store_org_knowledge(chunks, org_id, doc_id=str(doc.id))
            print(f"  OK  {doc.filename}: {len(chunks)} chunks (doc_id={doc.id})")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {doc.filename}: {exc}")

    print(f"\nVerifying retrieval for organization {org_id}...")
    try:
        retriever = get_org_retriever(org_id)
        docs = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: retriever.invoke(
                    "company overview, role context, technical stack, team culture, processes, challenges"
                )
            ),
            timeout=60,
        )
        print(f"  retrieved {len(docs)} chunks")
        for d in docs[:5]:
            print(f"    - {d.metadata} | {d.page_content[:60]}...")
    except Exception as exc:  # noqa: BLE001
        print(f"  verification failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-index organization docs into Pinecone")
    parser.add_argument("org_id", help="Organization ID (UUID) to index")
    args = parser.parse_args()
    asyncio.run(index_org(args.org_id))


if __name__ == "__main__":
    main()
