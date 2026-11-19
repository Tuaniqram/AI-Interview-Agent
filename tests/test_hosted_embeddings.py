"""Hosted embeddings (Hugging Face Inference API) behave, degrade gracefully and never need PyTorch."""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from app.rag import embeddings as emb
from app.rag.embeddings import EMBEDDING_DIM, EmbeddingUnavailable, HostedEmbeddings

ROOT = Path(__file__).resolve().parent.parent


def _vec(text: str) -> list[float]:
    """A deterministic fake embedding that differs per text (so ordering mistakes are visible)."""
    seed = int(hashlib.sha256(text.encode()).hexdigest(), 16)
    return [((seed >> (i % 200)) & 7) + 1.0 + (i % 5) for i in range(EMBEDDING_DIM)]


class FakeHF:
    """Stands in for the Hugging Face endpoint; records requests and can be scripted to fail first."""

    def __init__(self, script=None, shape="vectors"):
        self.requests: list[httpx.Request] = []
        self.script = list(script or [])  # status codes / exceptions served first, then normal answers
        self.shape = shape

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, Exception):
                raise item
            if item != 200:
                return httpx.Response(item, json={"error": "scripted"})
        inputs = json.loads(request.content)["inputs"]
        if self.shape == "vectors":
            body = [_vec(t) for t in inputs]
        elif self.shape == "flat":
            body = _vec(inputs[0])
        elif self.shape == "tokens":
            body = [[_vec(t), _vec(t + "x")] for t in inputs]  # two "tokens" per text
        elif self.shape == "short":
            body = [[1.0, 2.0, 3.0] for _ in inputs]
        elif self.shape == "count":
            body = [_vec(inputs[0])]
        return httpx.Response(200, json=body)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(fake, **kw):
    sleeps: list[float] = []
    clock = kw.pop("clock", Clock())
    e = HostedEmbeddings("hf_test_token", transport=httpx.MockTransport(fake), sleep=sleeps.append, clock=clock, **kw)
    e.sleeps, e.clock = sleeps, clock  # for assertions
    return e


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def test_query_is_a_normalized_384_vector_and_request_is_well_formed():
    fake = FakeHF()
    e = make(fake)
    v = e.embed_query("hello world")
    assert len(v) == EMBEDDING_DIM and abs(_norm(v) - 1.0) < 1e-9
    req = fake.requests[0]
    assert req.headers["authorization"] == "Bearer hf_test_token"
    assert "all-MiniLM-L6-v2" in str(req.url) and "feature-extraction" in str(req.url)
    assert json.loads(req.content) == {"inputs": ["hello world"], "truncate": True}


def test_documents_keep_their_order_across_batches():
    fake = FakeHF()
    e = make(fake, batch_size=32)
    texts = [f"question number {i}" for i in range(70)]
    out = e.embed_documents(texts)
    assert len(fake.requests) == 3  # 32 + 32 + 6
    for text, vec in zip(texts, out):
        expected = emb._normalize(_vec(text))
        assert all(abs(a - b) < 1e-9 for a, b in zip(vec, expected)), text


def test_repeated_texts_are_served_from_cache():
    fake = FakeHF()
    e = make(fake)
    e.embed_documents(["a", "b", "c"])
    assert len(fake.requests) == 1
    e.embed_documents(["a", "b", "c"])  # all cached
    assert len(fake.requests) == 1
    e.embed_documents(["a", "d"])       # only "d" is new
    assert len(fake.requests) == 2
    assert json.loads(fake.requests[1].content)["inputs"] == ["d"]


def test_returned_vectors_are_copies_not_the_cached_objects():
    e = make(FakeHF())
    first = e.embed_query("x")
    first[0] = 999.0
    assert e.embed_query("x")[0] != 999.0


def test_transient_errors_are_retried_with_backoff():
    fake = FakeHF(script=[503, 429, 200])
    e = make(fake, max_retries=2)
    assert len(e.embed_query("hello")) == EMBEDDING_DIM
    assert len(fake.requests) == 3
    assert e.sleeps == [0.5, 1.0]


def test_timeouts_are_retried():
    fake = FakeHF(script=[httpx.ConnectTimeout("slow"), 200])
    e = make(fake)
    assert len(e.embed_query("hello")) == EMBEDDING_DIM
    assert len(fake.requests) == 2


def test_gives_up_after_the_retries_and_then_opens_the_circuit_breaker():
    fake = FakeHF(script=[503] * 20)
    e = make(fake, max_retries=1, breaker_failures=2, breaker_seconds=60)
    for _ in range(2):  # two failed calls (each = 2 attempts) trip the breaker
        with pytest.raises(EmbeddingUnavailable):
            e.embed_query("hello")
    sent = len(fake.requests)
    assert sent == 4
    with pytest.raises(EmbeddingUnavailable, match="circuit"):  # fails at once, no network
        e.embed_query("another")
    assert len(fake.requests) == sent
    e.clock.now += 61  # breaker window over: it tries again
    fake.script = []
    assert len(e.embed_query("another")) == EMBEDDING_DIM
    assert len(fake.requests) == sent + 1


def test_bad_token_fails_immediately_with_a_clear_message():
    fake = FakeHF(script=[401])
    e = make(fake)
    with pytest.raises(EmbeddingUnavailable, match="HF_TOKEN"):
        e.embed_query("hello")
    assert len(fake.requests) == 1 and e.sleeps == []


def test_a_rejected_optional_parameter_is_dropped_and_remembered():
    fake = FakeHF(script=[422])
    e = make(fake)
    assert len(e.embed_query("hello")) == EMBEDDING_DIM
    assert "truncate" in json.loads(fake.requests[0].content)
    assert "truncate" not in json.loads(fake.requests[1].content)
    e.embed_query("second text")
    assert "truncate" not in json.loads(fake.requests[2].content)


def test_a_single_flat_vector_is_accepted():
    assert len(make(FakeHF(shape="flat")).embed_query("hello")) == EMBEDDING_DIM


def test_token_level_output_is_mean_pooled():
    v = make(FakeHF(shape="tokens")).embed_query("hello")
    mean = [(a + b) / 2 for a, b in zip(_vec("hello"), _vec("hellox"))]
    expected = emb._normalize(mean)
    assert all(abs(a - b) < 1e-9 for a, b in zip(v, expected))


@pytest.mark.parametrize("shape", ["short", "count"])
def test_malformed_answers_are_rejected(shape):
    texts = ["one", "two"] if shape == "count" else ["one"]
    with pytest.raises(EmbeddingUnavailable):
        make(FakeHF(shape=shape), max_retries=0).embed_documents(texts)


def test_a_token_is_required():
    with pytest.raises(ValueError):
        HostedEmbeddings("")


# ---- backend selection ---------------------------------------------------------------------------------------
@pytest.fixture
def clean_env(monkeypatch):
    for k in ("EMBEDDING_BACKEND", "HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_auto_uses_hosted_when_a_token_is_set_and_the_local_model_is_not_installed(clean_env):
    clean_env.setenv("HF_TOKEN", "hf_x")
    clean_env.setattr(emb, "local_available", lambda: False)
    assert emb.hosted_backend_selected() is True
    assert isinstance(emb.build_embeddings(), HostedEmbeddings)


def test_auto_keeps_the_local_model_when_it_is_installed_even_with_a_token(clean_env):
    """A developer machine must behave as before even if an HF_TOKEN is set in its .env."""
    clean_env.setenv("HF_TOKEN", "hf_x")
    clean_env.setattr(emb, "local_available", lambda: True)
    assert emb.hosted_backend_selected() is False


def test_the_alternative_token_name_works(clean_env):
    clean_env.setenv("HUGGINGFACEHUB_API_TOKEN", "hf_y")
    clean_env.setattr(emb, "local_available", lambda: False)
    assert isinstance(emb.build_embeddings(), HostedEmbeddings)


def test_auto_without_a_token_means_local(clean_env):
    assert emb.hosted_backend_selected() is False


def test_hosted_without_a_token_is_an_error(clean_env):
    clean_env.setenv("EMBEDDING_BACKEND", "hosted")
    with pytest.raises(RuntimeError, match="HF_TOKEN"):
        emb.build_embeddings()


def test_hosted_can_be_forced_even_when_the_local_model_is_installed(clean_env):
    clean_env.setenv("EMBEDDING_BACKEND", "hosted")
    clean_env.setenv("HF_TOKEN", "hf_x")
    clean_env.setattr(emb, "local_available", lambda: True)
    assert emb.hosted_backend_selected() is True


def test_local_wins_even_when_a_token_is_set(clean_env):
    clean_env.setenv("EMBEDDING_BACKEND", "local")
    clean_env.setenv("HF_TOKEN", "hf_x")
    assert emb.hosted_backend_selected() is False


def test_an_unknown_backend_name_is_rejected(clean_env):
    clean_env.setenv("EMBEDDING_BACKEND", "cloud")
    with pytest.raises(ValueError):
        emb.hosted_backend_selected()


def test_local_without_sentence_transformers_explains_how_to_fix_it(clean_env):
    clean_env.setenv("EMBEDDING_BACKEND", "local")
    clean_env.setitem(sys.modules, "langchain_huggingface", None)  # makes the import raise ImportError
    with pytest.raises(RuntimeError, match="requirements-local"):
        emb.build_embeddings()


# ---- the point of the exercise: no PyTorch in the web process ---------------------------------------------------
def test_the_whole_app_and_the_hosted_backend_run_without_pytorch():
    code = r"""
import sys, importlib.abc

class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] in ('torch', 'sentence_transformers', 'transformers'):
            raise ImportError('blocked: ' + name)

sys.meta_path.insert(0, Block())
import httpx
import app.main                      # every router, middleware and service
from app.rag.embeddings import HostedEmbeddings
from app.rag.pinecone_store import get_embedding

def handler(request):
    import json
    return httpx.Response(200, json=[[0.1] * 384 for _ in json.loads(request.content)['inputs']])

e = HostedEmbeddings('hf_x', transport=httpx.MockTransport(handler))
assert len(e.embed_query('hello')) == 384
loaded = [m for m in sys.modules if m.split('.')[0] in ('torch', 'sentence_transformers', 'transformers')]
assert not loaded, loaded
print('OK')
"""
    done = subprocess.run([sys.executable, "-W", "ignore", "-c", code], cwd=ROOT, capture_output=True, text=True,
                          timeout=240)
    assert done.returncode == 0 and "OK" in done.stdout, done.stderr[-1500:]
