"""Where uploaded CVs live.

* ``local`` (default): files under ``resumes/`` on this server's disk. Fine for one machine; files
  vanish on a redeploy to most hosts and are invisible to other instances.
* ``supabase``: a private Supabase Storage bucket. Survives redeploys, shared by every instance.
  Enable with ``CV_STORAGE=supabase`` plus ``SUPABASE_SERVICE_KEY`` (a *secret* / service-role key:
  the publishable key cannot write to a private bucket). The bucket (``CV_STORAGE_BUCKET``, default
  ``cvs``) is created as private on first use.

A stored CV is identified by a *ref* string kept in ``candidate_documents.document_metadata.path``
and ``candidate_profiles.resume_url``: a relative path for local files (also every pre-existing
value) or ``supabase://<bucket>/<key>``.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LOCAL_DIR = Path("resumes")
SUPABASE_SCHEME = "supabase://"


class CVStorageError(RuntimeError):
    pass


def _backend() -> str:
    return (os.getenv("CV_STORAGE") or "local").strip().lower()


def _bucket() -> str:
    return (os.getenv("CV_STORAGE_BUCKET") or "cvs").strip()


def _supabase_config() -> tuple[str, str]:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY") or ""
    if not url or not key:
        raise CVStorageError("CV_STORAGE=supabase needs SUPABASE_URL and SUPABASE_SERVICE_KEY")
    return url, key


def _headers(key: str, **extra: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "apikey": key, **extra}


# Overridable in tests (httpx.MockTransport); one client per call keeps this free of event-loop state.
_transport: Optional[httpx.AsyncBaseTransport] = None
_bucket_ready: set[str] = set()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30, transport=_transport)


async def _ensure_bucket(client: httpx.AsyncClient, url: str, key: str, bucket: str) -> None:
    if bucket in _bucket_ready:
        return
    r = await client.post(
        f"{url}/storage/v1/bucket",
        headers=_headers(key, **{"Content-Type": "application/json"}),
        json={"id": bucket, "name": bucket, "public": False, "allowed_mime_types": ["application/pdf"]},
    )
    body = r.text.lower()
    if r.status_code in (200, 201) or "already exists" in body or "duplicate" in body or r.status_code == 409:
        _bucket_ready.add(bucket)
        return
    raise CVStorageError(f"could not create storage bucket {bucket!r}: HTTP {r.status_code}")


def _safe_local_path(ref: str) -> Path:
    """Resolve a local ref and refuse anything outside the CV directory."""
    path = Path(ref).resolve()
    if not path.is_relative_to(LOCAL_DIR.resolve()):
        raise CVStorageError("CV path outside the CV directory")
    return path


async def save(key: str, content: bytes) -> str:
    """Store ``content`` under ``key`` (e.g. ``<candidate_id>/<document_id>.pdf``); returns the ref."""
    if _backend() == "supabase":
        url, skey = _supabase_config()
        bucket = _bucket()
        async with _client() as client:
            await _ensure_bucket(client, url, skey, bucket)
            r = await client.post(
                f"{url}/storage/v1/object/{bucket}/{key}",
                headers=_headers(skey, **{"Content-Type": "application/pdf", "x-upsert": "true"}),
                content=content,
            )
        if r.status_code not in (200, 201):
            raise CVStorageError(f"CV upload failed: HTTP {r.status_code}")
        return f"{SUPABASE_SCHEME}{bucket}/{key}"

    path = LOCAL_DIR / key.replace("/", "-")

    def _write() -> None:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    await asyncio.get_running_loop().run_in_executor(None, _write)
    return str(path)


async def read(ref: str) -> Optional[bytes]:
    """The CV bytes, or ``None`` when the file is gone. Works for refs from either backend."""
    if not ref:
        return None
    if ref.startswith(SUPABASE_SCHEME):
        bucket, _, key = ref[len(SUPABASE_SCHEME):].partition("/")
        url, skey = _supabase_config()
        async with _client() as client:
            r = await client.get(f"{url}/storage/v1/object/{bucket}/{key}", headers=_headers(skey))
        if r.status_code == 404 or r.status_code == 400:
            return None
        if r.status_code != 200:
            raise CVStorageError(f"CV download failed: HTTP {r.status_code}")
        return r.content

    try:
        path = _safe_local_path(ref)
    except CVStorageError:
        return None
    if not path.is_file():
        return None
    return await asyncio.get_running_loop().run_in_executor(None, path.read_bytes)


async def delete(ref: str) -> None:
    """Best-effort removal (used by test-data cleanup)."""
    try:
        if ref.startswith(SUPABASE_SCHEME):
            bucket, _, key = ref[len(SUPABASE_SCHEME):].partition("/")
            url, skey = _supabase_config()
            async with _client() as client:
                await client.request(
                    "DELETE", f"{url}/storage/v1/object/{bucket}",
                    headers=_headers(skey, **{"Content-Type": "application/json"}), json={"prefixes": [key]},
                )
        else:
            path = _safe_local_path(ref)
            if path.is_file():
                path.unlink()
    except Exception:  # noqa: BLE001 - cleanup must not fail the caller
        logger.warning("Could not delete CV %s", ref, exc_info=True)
