"""Text embeddings for Pinecone retrieval and the question-similarity guard.

Two interchangeable backends, both producing the same 384-dimension vectors of ``all-MiniLM-L6-v2`` so the existing
Pinecone index and the similarity thresholds stay valid:

* ``hosted``  Hugging Face Inference API over HTTPS. Needs ``HF_TOKEN``. No PyTorch in the web process, which matters
              on small hosts: importing the app alone is ~330 MB, and the local model (PyTorch) does not fit in 512 MB.
* ``local``   ``sentence-transformers`` in-process (the original behaviour). Install ``requirements-local.txt``.

``EMBEDDING_BACKEND`` = ``auto`` (default: local when sentence-transformers is installed, otherwise hosted when
a token is set) | ``hosted`` | ``local``.

A hosted outage must never slow or break an interview: calls are retried briefly, repeated failures open a circuit
breaker so later calls fail at once, and every caller already treats a failed embedding as "no result".
"""
from __future__ import annotations

import logging
import math
import os
import threading
import time
from collections import OrderedDict
from typing import Callable, Optional

import httpx
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_RETRY_STATUSES = {429, 500, 502, 503, 504}


class EmbeddingUnavailable(RuntimeError):
    """The embedding service could not produce vectors (callers treat this as "no result")."""


class HostedEmbeddings(Embeddings):
    """Hugging Face Inference API ``feature-extraction`` for ``all-MiniLM-L6-v2``."""

    URL = "https://router.huggingface.co/hf-inference/models/{model}/pipeline/feature-extraction"

    def __init__(
        self,
        token: str,
        *,
        model: str = EMBEDDING_MODEL,
        timeout: float = 8.0,
        batch_size: int = 32,
        max_retries: int = 2,
        cache_size: int = 4096,
        breaker_failures: int = 2,
        breaker_seconds: float = 60.0,
        transport: Optional[httpx.BaseTransport] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not token:
            raise ValueError("HostedEmbeddings needs a Hugging Face token (HF_TOKEN)")
        self._url = self.URL.format(model=model)
        self._client = httpx.Client(
            timeout=timeout, transport=transport, headers={"Authorization": f"Bearer {token}"}
        )
        self._batch_size = max(1, batch_size)
        self._max_retries = max(0, max_retries)
        self._sleep = sleep
        self._clock = clock
        # Embedding the same text twice is common (the similarity guard re-embeds every earlier question each turn).
        self._cache: "OrderedDict[str, list[float]]" = OrderedDict()
        self._cache_size = max(0, cache_size)
        self._lock = threading.Lock()
        # Circuit breaker: after consecutive failed calls, fail fast for a while instead of waiting on timeouts.
        self._breaker_failures = breaker_failures
        self._breaker_seconds = breaker_seconds
        self._failures = 0
        self._down_until = 0.0
        # Some deployments reject the optional ``truncate`` parameter; remember that once and stop sending it.
        self._send_options = True
        self._warned_token_level = False

    # ---- public (LangChain Embeddings interface) -------------------------------------------------------------
    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        texts = [t if isinstance(t, str) else str(t) for t in texts]
        results: dict[int, list[float]] = {}
        missing: list[tuple[int, str]] = []
        for i, text in enumerate(texts):
            hit = self._cache_get(text)
            if hit is not None:
                results[i] = hit
            else:
                missing.append((i, text))
        for start in range(0, len(missing), self._batch_size):
            chunk = missing[start:start + self._batch_size]
            vectors = self._embed_batch([t for _, t in chunk])
            for (i, text), vec in zip(chunk, vectors):
                results[i] = vec
                self._cache_put(text, vec)
        return [list(results[i]) for i in range(len(texts))]

    # ---- cache -------------------------------------------------------------------------------------------------
    def _cache_get(self, text: str) -> Optional[list[float]]:
        if not self._cache_size:
            return None
        with self._lock:
            vec = self._cache.get(text)
            if vec is not None:
                self._cache.move_to_end(text)
            return vec

    def _cache_put(self, text: str, vec: list[float]) -> None:
        if not self._cache_size:
            return
        with self._lock:
            self._cache[text] = vec
            self._cache.move_to_end(text)
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)

    # ---- network -----------------------------------------------------------------------------------------------
    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        if self._clock() < self._down_until:
            raise EmbeddingUnavailable("hosted embeddings are temporarily unavailable (circuit open)")
        last: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                vectors = self._parse(self._post(batch), len(batch))
                self._failures = 0
                return vectors
            except EmbeddingUnavailable as exc:
                last = exc
                if not getattr(exc, "retryable", False):
                    break
            if attempt < self._max_retries:
                self._sleep(min(4.0, 0.5 * (2 ** attempt)))
        self._failures += 1
        if self._failures >= self._breaker_failures:
            self._down_until = self._clock() + self._breaker_seconds
            logger.warning("Hosted embeddings failing; pausing calls for %.0fs: %s", self._breaker_seconds, last)
        raise EmbeddingUnavailable(str(last)) from last

    def _post(self, batch: list[str]):
        payload: dict = {"inputs": batch}
        if self._send_options:
            payload["truncate"] = True  # match the local model, which silently truncates long text
        try:
            response = self._client.post(self._url, json=payload)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _retryable(f"embedding request failed: {type(exc).__name__}") from exc
        if response.status_code in (400, 422) and self._send_options:
            self._send_options = False  # retry once without the optional parameter
            return self._post(batch)
        if response.status_code in _RETRY_STATUSES:
            raise _retryable(f"embedding service returned HTTP {response.status_code}")
        if response.status_code in (401, 403):
            raise EmbeddingUnavailable(
                f"Hugging Face rejected the token (HTTP {response.status_code}); check HF_TOKEN and its "
                "'Inference Providers' permission"
            )
        if response.status_code >= 400:
            raise EmbeddingUnavailable(f"embedding service returned HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise EmbeddingUnavailable("embedding service returned invalid JSON") from exc

    def _parse(self, body, expected: int) -> list[list[float]]:
        if not isinstance(body, list) or not body:
            raise EmbeddingUnavailable("embedding service returned an unexpected response")
        if expected == 1 and isinstance(body[0], (int, float)):
            body = [body]  # a single flat vector
        if len(body) != expected:
            raise EmbeddingUnavailable(f"expected {expected} embeddings, got {len(body)}")
        vectors: list[list[float]] = []
        for item in body:
            vec = self._pool(item)
            if len(vec) != EMBEDDING_DIM or not all(math.isfinite(x) for x in vec):
                raise EmbeddingUnavailable(f"embedding has {len(vec)} dimensions, expected {EMBEDDING_DIM}")
            vectors.append(_normalize(vec))
        return vectors

    def _pool(self, item) -> list[float]:
        if item and isinstance(item[0], (int, float)):
            return [float(x) for x in item]
        if item and isinstance(item[0], list):  # token-level output: mean-pool it
            if not self._warned_token_level:
                self._warned_token_level = True
                logger.warning("Embedding service returned token-level vectors; mean-pooling them")
            n = len(item)
            return [sum(token[d] for token in item) / n for d in range(len(item[0]))]
        raise EmbeddingUnavailable("embedding service returned an unexpected vector shape")


def _retryable(message: str) -> EmbeddingUnavailable:
    exc = EmbeddingUnavailable(message)
    exc.retryable = True  # type: ignore[attr-defined]
    return exc


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec


def hf_token() -> Optional[str]:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN") or None


def _backend_choice() -> str:
    backend = os.getenv("EMBEDDING_BACKEND", "auto").strip().lower()
    if backend not in ("auto", "hosted", "local"):
        raise ValueError(f"EMBEDDING_BACKEND must be auto, hosted or local, not {backend!r}")
    return backend


def local_available() -> bool:
    """True when the local model's library is installed (checked without importing it)."""
    import importlib.util

    return importlib.util.find_spec("sentence_transformers") is not None


def hosted_backend_selected() -> bool:
    """True when embeddings go to the hosted API (nothing heavy to load in this process).

    ``auto`` prefers the local model when it is installed, so a developer machine behaves exactly as before even when
    an HF_TOKEN happens to be set; a deployment without PyTorch uses the hosted API when a token is set.
    """
    backend = _backend_choice()
    return backend == "hosted" or (backend == "auto" and bool(hf_token()) and not local_available())


def build_embeddings() -> Embeddings:
    """Create the configured backend (see module docstring)."""
    token = hf_token()
    if hosted_backend_selected():
        if not token:
            raise RuntimeError("EMBEDDING_BACKEND=hosted needs HF_TOKEN to be set")
        logger.info("Embedding backend: hosted (Hugging Face Inference API)")
        return HostedEmbeddings(token)
    try:
        from langchain_huggingface import HuggingFaceEmbeddings  # imports sentence-transformers / PyTorch
    except ImportError as exc:
        raise RuntimeError(
            "Local embeddings need sentence-transformers (pip install -r requirements-local.txt). "
            "Or set HF_TOKEN to use the hosted backend."
        ) from exc
    logger.info("Embedding backend: local (sentence-transformers in this process)")
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
