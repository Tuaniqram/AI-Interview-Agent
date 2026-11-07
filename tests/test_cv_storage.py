"""CV storage: local disk by default, Supabase Storage when configured (tested against a fake
HTTP server, so no real project is touched)."""
import httpx
import pytest

from app.services import cv_storage

PDF = b"%PDF-1.4 fake cv"


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setenv("CV_STORAGE", "local")
    monkeypatch.setattr(cv_storage, "LOCAL_DIR", tmp_path)
    return tmp_path


async def test_local_save_and_read_roundtrip(local):
    ref = await cv_storage.save("cand-1/doc-1.pdf", PDF)
    assert not ref.startswith("supabase://")
    assert (local / "cand-1-doc-1.pdf").read_bytes() == PDF
    assert await cv_storage.read(ref) == PDF


async def test_local_read_refuses_paths_outside_the_cv_directory(local, tmp_path_factory):
    outside = tmp_path_factory.mktemp("elsewhere") / "secret.pdf"
    outside.write_bytes(b"secret")
    assert await cv_storage.read(str(outside)) is None
    assert await cv_storage.read(str(local / ".." / "x.pdf")) is None


async def test_local_missing_file_reads_as_none(local):
    assert await cv_storage.read(str(local / "gone.pdf")) is None
    assert await cv_storage.read("") is None


async def test_local_delete(local):
    ref = await cv_storage.save("c/d.pdf", PDF)
    await cv_storage.delete(ref)
    assert await cv_storage.read(ref) is None


class FakeSupabase:
    """Minimal Supabase Storage: bucket create, object upload/download/delete."""

    def __init__(self):
        self.buckets: dict[str, dict] = {}
        self.objects: dict[str, bytes] = {}
        self.auth_headers: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.auth_headers.append(request.headers.get("authorization", ""))
        path = request.url.path
        if request.method == "POST" and path == "/storage/v1/bucket":
            body = request.read()
            import json

            data = json.loads(body)
            if data["id"] in self.buckets:
                return httpx.Response(400, json={"message": "The resource already exists"})
            self.buckets[data["id"]] = data
            return httpx.Response(200, json={"name": data["id"]})
        if path.startswith("/storage/v1/object/"):
            rest = path[len("/storage/v1/object/"):]
            if request.method == "POST":
                self.objects[rest] = request.read()
                return httpx.Response(200, json={"Key": rest})
            if request.method == "GET":
                return httpx.Response(200, content=self.objects[rest]) if rest in self.objects else httpx.Response(400, json={"error": "not_found"})
            if request.method == "DELETE":
                import json

                bucket = rest
                for key in json.loads(request.read())["prefixes"]:
                    self.objects.pop(f"{bucket}/{key}", None)
                return httpx.Response(200, json=[])
        return httpx.Response(404)


@pytest.fixture
def supabase(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setenv("CV_STORAGE", "supabase")
    monkeypatch.setenv("CV_STORAGE_BUCKET", "cvs")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
    monkeypatch.setattr(cv_storage, "_transport", httpx.MockTransport(fake.handler))
    monkeypatch.setattr(cv_storage, "_bucket_ready", set())
    return fake


async def test_supabase_creates_a_private_bucket_and_roundtrips(supabase):
    ref = await cv_storage.save("cand-1/doc-1.pdf", PDF)
    assert ref == "supabase://cvs/cand-1/doc-1.pdf"
    assert supabase.buckets["cvs"]["public"] is False  # CVs are never public
    assert await cv_storage.read(ref) == PDF
    assert all(h == "Bearer service-key" for h in supabase.auth_headers)


async def test_supabase_existing_bucket_is_fine(supabase):
    supabase.buckets["cvs"] = {"id": "cvs", "public": False}
    ref = await cv_storage.save("c/d.pdf", PDF)
    assert await cv_storage.read(ref) == PDF


async def test_supabase_missing_object_reads_as_none(supabase):
    assert await cv_storage.read("supabase://cvs/nope.pdf") is None


async def test_supabase_delete(supabase):
    ref = await cv_storage.save("c/d.pdf", PDF)
    await cv_storage.delete(ref)
    assert await cv_storage.read(ref) is None


async def test_supabase_without_a_service_key_fails_clearly(monkeypatch):
    monkeypatch.setenv("CV_STORAGE", "supabase")
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    with pytest.raises(cv_storage.CVStorageError, match="SUPABASE_SERVICE_KEY"):
        await cv_storage.save("c/d.pdf", PDF)


async def test_old_local_refs_still_read_after_switching_to_supabase(local, monkeypatch):
    ref = await cv_storage.save("old/cv.pdf", PDF)  # stored while CV_STORAGE=local
    monkeypatch.setenv("CV_STORAGE", "supabase")
    assert await cv_storage.read(ref) == PDF  # reads go by the ref, not the current backend
