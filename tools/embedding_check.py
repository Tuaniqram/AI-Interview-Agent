"""Check that the hosted embeddings match the local model, and that the hosted service works at all.

    python tools/embedding_check.py

Needs HF_TOKEN in .env (or the environment) AND the local model: pip install -r requirements-local.txt.
Prints, for each sample text, the cosine similarity between the local and the hosted vector (1.0 = identical), the
hosted latency, and a verdict. A pass means the existing Pinecone index and the question-similarity thresholds
(tuned on the local model) are still valid with the hosted backend. Exit code 0 = pass, 1 = fail, 2 = cannot run.
"""
import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

THRESHOLD = 0.995  # same model, so ~1.0; this leaves room for float / ONNX-vs-PyTorch differences

SAMPLES = [
    "Tell me about a time you debugged a production incident under pressure.",
    "How would you design a rate limiter for a multi-tenant API?",
    "Explain the difference between optimistic and pessimistic locking.",
    "What trade-offs did you consider when choosing PostgreSQL over a document store?",
    "Describe how you would roll out a risky database migration with no downtime.",
    "We are a fintech company building payments infrastructure; we value ownership and clear communication.",
    "Retrieve documents related to: Backend Developer, company requirements",
    "Candidate weak areas to address: caching, concurrency, observability",
    "x",
    "Ünïcödé tëxt with accents, emoji 🚀 and symbols: ≈ ∑ ✓",
    # long enough to need truncation (the local model cuts at 256 tokens; the hosted call asks for the same)
    " ".join(["Our platform ingests events, validates them, enriches them with reference data and writes the result "
              "to a warehouse while keeping an audit trail for every transformation."] * 12),
]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def main() -> int:
    from app.rag.embeddings import EMBEDDING_MODEL, EmbeddingUnavailable, HostedEmbeddings, hf_token

    token = hf_token()
    if not token:
        print("HF_TOKEN is not set (put it in .env). Nothing to check.")
        return 2
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        local = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    except Exception as exc:  # noqa: BLE001
        print(f"Cannot load the local model ({type(exc).__name__}: {exc}).\nInstall it: pip install -r requirements-local.txt")
        return 2

    hosted = HostedEmbeddings(token, timeout=30.0, max_retries=3)
    print(f"model {EMBEDDING_MODEL}\n")

    try:
        t = time.time()
        hosted_vecs = hosted.embed_documents(SAMPLES)
        batch_s = time.time() - t
        t = time.time()
        hosted.embed_query("single query latency probe")
        single_s = time.time() - t
    except EmbeddingUnavailable as exc:
        print(f"HOSTED SERVICE FAILED: {exc}")
        print("If this says the token was rejected: create a token with the 'Make calls to Inference Providers'"
              " permission. If it says HTTP 404 or 422, the model or route is not served for your account.")
        return 1

    local_vecs = local.embed_documents(SAMPLES)
    worst = 1.0
    for text, a, b in zip(SAMPLES, local_vecs, hosted_vecs):
        sim = cosine(a, b)
        worst = min(worst, sim)
        shown = text if len(text) <= 56 else text[:53] + "..."
        print(f"  {sim:.6f}  {'OK  ' if sim >= THRESHOLD else 'FAIL'}  {shown}")

    print(f"\nlowest similarity : {worst:.6f}   (pass needs >= {THRESHOLD})")
    print(f"hosted latency    : {batch_s:.2f}s for {len(SAMPLES)} texts in one call, {single_s:.2f}s for one query")
    ok = worst >= THRESHOLD
    print("\nPASS: hosted vectors match the local model." if ok else
          "\nFAIL: hosted vectors differ from the local model. Do NOT use the hosted backend with the existing "
          "index until this is understood.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
