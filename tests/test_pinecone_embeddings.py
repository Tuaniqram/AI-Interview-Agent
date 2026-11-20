"""Pinecone's free hosted embeddings: behaviour, backend selection, separate namespaces and the similarity guard."""
import hashlib
import math
import sys

import pytest

from app.rag import embeddings as emb
from app.rag import pinecone_store as store
from app.rag.embeddings import EMBEDDING_DIM, EmbeddingUnavailable, PineconeEmbeddings

MB = 1048576


def _vec(text: str) -> list[float]:
    seed = int(hashlib.sha256(text.encode()).hexdigest(), 16)
    return [((seed >> (i % 200)) & 7) + 1.0 + (i % 5) for i in range(EMBEDDING_DIM)]


class ApiError(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status = status


class FakePinecone:
    """Stands in for ``Pinecone(...)``: records ``inference.embed`` calls; can fail first."""

    def __init__(self, script=None, wrong_dim=False, wrong_count=False):
        self.calls: list[dict] = []
        self.script = list(script or [])
        self.wrong_dim, self.wrong_count = wrong_dim, wrong_count
        self.inference = self  # client.inference.embed(...)

    def embed(self, model, inputs, parameters):
        self.calls.append({"model": model, "inputs": list(inputs), "parameters": dict(parameters)})
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, Exception):
                raise item
        if self.wrong_count:
            inputs = inputs[:-1]
        size = 10 if self.wrong_dim else EMBEDDING_DIM
        return [{"values": _vec(t)[:size]} for t in inputs]


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(fake=None, **kw):
    fake = fake or FakePinecone()
    sleeps: list[float] = []
    clock = kw.pop("clock", Clock())
    e = PineconeEmbeddings(client=fake, sleep=sleeps.append, clock=clock, **kw)
    e.sleeps, e.clock, e.fake = sleeps, clock, fake
    return e


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


# ---- the backend ---------------------------------------------------------------------------------------------------
def test_query_and_documents_use_the_right_input_types_and_384_dimensions():
    e = make()
    e.embed_query("who are we")
    e.embed_documents(["a passage"])
    q, d = e.fake.calls
    assert q["model"] == "llama-text-embed-v2" and q["parameters"] == {"input_type": "query", "dimension": 384, "truncate": "END"}
    assert d["parameters"]["input_type"] == "passage"


def test_vectors_are_normalized_and_in_order_across_batches():
    e = make(batch_size=64)
    texts = [f"chunk number {i}" for i in range(150)]
    out = e.embed_documents(texts)
    assert [len(c["inputs"]) for c in e.fake.calls] == [64, 64, 22]
    for text, vec in zip(texts, out):
        assert len(vec) == EMBEDDING_DIM and abs(_norm(vec) - 1.0) < 1e-9
        assert all(abs(a - b) < 1e-9 for a, b in zip(vec, emb._normalize(_vec(text))))


def test_a_query_and_a_passage_with_the_same_text_are_cached_separately():
    e = make()
    e.embed_query("same text")
    e.embed_query("same text")                 # cached
    e.embed_documents(["same text"])           # a different input type: must be requested
    assert len(e.fake.calls) == 2


def test_only_new_texts_are_requested():
    e = make()
    e.embed_documents(["a", "b"])
    e.embed_documents(["a", "b", "c"])
    assert e.fake.calls[1]["inputs"] == ["c"]


def test_busy_responses_are_retried_with_backoff():
    e = make(FakePinecone(script=[ApiError(429), ApiError(503)]), max_retries=2)
    assert len(e.embed_query("x")) == EMBEDDING_DIM
    assert len(e.fake.calls) == 3 and e.sleeps == [0.5, 1.0]


def test_network_errors_without_a_status_are_retried():
    e = make(FakePinecone(script=[ConnectionError("reset")]))
    assert len(e.embed_query("x")) == EMBEDDING_DIM
    assert len(e.fake.calls) == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_rejections_are_not_retried(status):
    e = make(FakePinecone(script=[ApiError(status)] * 5))
    with pytest.raises(EmbeddingUnavailable):
        e.embed_query("x")
    assert len(e.fake.calls) == 1 and e.sleeps == []


def test_repeated_failures_open_the_circuit_breaker_and_then_close_it():
    e = make(FakePinecone(script=[ApiError(503)] * 20), max_retries=1, breaker_failures=2, breaker_seconds=60)
    for _ in range(2):
        with pytest.raises(EmbeddingUnavailable):
            e.embed_query("x")
    sent = len(e.fake.calls)
    with pytest.raises(EmbeddingUnavailable, match="circuit"):
        e.embed_query("y")
    assert len(e.fake.calls) == sent
    e.clock.now += 61
    e.fake.script = []
    assert len(e.embed_query("y")) == EMBEDDING_DIM


@pytest.mark.parametrize("kw", [{"wrong_dim": True}, {"wrong_count": True}])
def test_malformed_answers_are_rejected(kw):
    with pytest.raises(EmbeddingUnavailable):
        make(FakePinecone(**kw), max_retries=0).embed_documents(["one", "two"])


def test_a_key_is_required_when_no_client_is_given():
    with pytest.raises(ValueError):
        PineconeEmbeddings()


def test_it_is_marked_as_not_calibrated_for_the_similarity_guard():
    assert PineconeEmbeddings.calibrated_for_similarity is False
    assert PineconeEmbeddings.namespace_suffix == "__llama-text-embed-v2-384"


# ---- which backend `auto` picks ---------------------------------------------------------------------------------------
@pytest.fixture
def env(monkeypatch):
    for k in ("EMBEDDING_BACKEND", "HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "PINECONE_API_KEY", "EMBEDDING_LOCAL_MIN_FREE_MB"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(emb, "_cgroup_used_bytes", lambda: None)
    monkeypatch.setattr(emb, "_cgroup_limit_bytes", lambda: None)
    monkeypatch.setattr(emb, "_rss_bytes", lambda: None)
    return monkeypatch


def container(env, limit_mb, used_mb):
    env.setattr(emb, "_cgroup_limit_bytes", lambda: int(limit_mb * MB))
    env.setattr(emb, "_cgroup_used_bytes", lambda: int(used_mb * MB))


def test_auto_prefers_the_local_model_when_it_fits(env):
    env.setattr(emb, "local_available", lambda: True)
    env.setenv("PINECONE_API_KEY", "pc_x")
    container(env, 2048, 330)
    assert emb.choose_backend() == "local" and emb.embedding_namespace_suffix() == ""


def test_auto_uses_pinecone_when_the_local_model_does_not_fit(env):
    """The case that matters: a 512 MB host. Torch is installed but there is no room, and a Pinecone key exists."""
    env.setattr(emb, "local_available", lambda: True)
    env.setenv("PINECONE_API_KEY", "pc_x")
    container(env, 512, 330)
    assert emb.choose_backend() == "pinecone"
    assert emb.hosted_backend_selected() is True
    assert emb.embedding_namespace_suffix() == "__llama-text-embed-v2-384"


def test_auto_falls_back_to_hugging_face_only_without_a_pinecone_key(env):
    env.setattr(emb, "local_available", lambda: True)
    env.setenv("HF_TOKEN", "hf_x")
    container(env, 512, 330)
    assert emb.choose_backend() == "hosted"
    env.setenv("PINECONE_API_KEY", "pc_x")
    assert emb.choose_backend() == "pinecone"


def test_auto_with_no_room_and_no_remote_option_stays_local_and_refuses_with_a_reason(env):
    env.setattr(emb, "local_available", lambda: True)
    container(env, 512, 330)
    assert emb.choose_backend() == "local"
    with pytest.raises(EmbeddingUnavailable, match="not enough memory"):
        emb.build_embeddings()


def test_auto_without_the_local_library_uses_pinecone_then_hugging_face(env):
    env.setattr(emb, "local_available", lambda: False)
    env.setenv("HF_TOKEN", "hf_x")
    assert emb.choose_backend() == "hosted"
    env.setenv("PINECONE_API_KEY", "pc_x")
    assert emb.choose_backend() == "pinecone"


def test_explicit_choices_win(env):
    env.setattr(emb, "local_available", lambda: True)
    env.setenv("PINECONE_API_KEY", "pc_x")
    env.setenv("EMBEDDING_BACKEND", "pinecone")
    assert emb.choose_backend() == "pinecone"
    env.setenv("EMBEDDING_BACKEND", "local")
    assert emb.choose_backend() == "local"
    env.setenv("EMBEDDING_BACKEND", "off")
    assert emb.choose_backend() == "off"


def test_explicit_pinecone_without_a_key_is_an_error(env):
    env.setenv("EMBEDDING_BACKEND", "pinecone")
    with pytest.raises(RuntimeError, match="PINECONE_API_KEY"):
        emb.build_embeddings()


def test_build_embeddings_creates_the_pinecone_backend(env):
    env.setenv("EMBEDDING_BACKEND", "pinecone")
    env.setenv("PINECONE_API_KEY", "pc_x")
    built = {}
    env.setattr(emb, "PineconeEmbeddings", type("Spy", (), {"namespace_suffix": "s", "__init__": lambda self, key: built.update(key=key)}))
    emb.build_embeddings()
    assert built == {"key": "pc_x"}


# ---- namespaces: the database value never changes; the Pinecone one carries the model ---------------------------------
def test_the_logical_namespace_is_unchanged_whatever_the_backend(env):
    env.setenv("EMBEDDING_BACKEND", "pinecone")
    assert store.org_namespace("abc-123") == "department_abc-123"


def test_the_physical_namespace_gets_a_suffix_only_for_pinecone(env):
    env.setenv("EMBEDDING_BACKEND", "local")
    assert store.physical_namespace("abc-123") == "department_abc-123"
    env.setenv("EMBEDDING_BACKEND", "hosted")
    assert store.physical_namespace("abc-123") == "department_abc-123"          # same MiniLM vectors
    env.setenv("EMBEDDING_BACKEND", "pinecone")
    assert store.physical_namespace("abc-123") == "department_abc-123__llama-text-embed-v2-384"


def test_storing_and_searching_use_the_physical_namespace(env, monkeypatch):
    env.setenv("EMBEDDING_BACKEND", "pinecone")
    seen = {}
    monkeypatch.setattr(store, "get_embedding", lambda: "embedder")

    class FakeStore:
        @classmethod
        def from_documents(cls, documents, embedding, index_name, namespace):
            seen["store"] = namespace
            return "vs"

        def __init__(self, index_name, embedding, namespace):
            seen["search"] = namespace

        def as_retriever(self, search_kwargs):
            return "retriever"

    monkeypatch.setattr(store, "PineconeVectorStore", FakeStore)
    store.store_org_knowledge([], "o1")
    store.get_org_retriever("o1")
    assert seen == {"store": "department_o1__llama-text-embed-v2-384", "search": "department_o1__llama-text-embed-v2-384"}


def test_deleting_a_document_clears_both_possible_namespaces(env, monkeypatch):
    env.setenv("EMBEDDING_BACKEND", "pinecone")
    deleted = []

    class Index:
        def delete(self, filter, namespace):
            deleted.append(namespace)

    monkeypatch.setattr(store, "get_index", lambda: Index())
    store.delete_org_knowledge("o1", "doc9")
    assert sorted(deleted) == ["department_o1", "department_o1__llama-text-embed-v2-384"]


# ---- the similarity guard ---------------------------------------------------------------------------------------------
def test_the_guard_uses_text_matching_when_the_embeddings_are_not_calibrated(monkeypatch):
    from app.agents.generation.question_similarity_guard import QuestionSimilarityGuard

    class Uncalibrated:
        calibrated_for_similarity = False

        def embed_query(self, t):
            pytest.fail("must not embed")

        embed_documents = embed_query

    monkeypatch.setattr(store, "get_embedding", lambda: Uncalibrated())
    guard = QuestionSimilarityGuard()
    assert guard._embedding_similarity("new question", ["old question"]) == (None, "")


def test_the_guard_still_uses_calibrated_embeddings(monkeypatch):
    from app.agents.generation.question_similarity_guard import QuestionSimilarityGuard

    class Calibrated:                               # no attribute: the MiniLM classes do not define it
        def embed_query(self, t):
            return [1.0, 0.0]

        def embed_documents(self, ts):
            return [[1.0, 0.0] for _ in ts]

    monkeypatch.setattr(store, "get_embedding", lambda: Calibrated())
    score, matched = QuestionSimilarityGuard()._embedding_similarity("a", ["b"])
    assert score == 1.0 and matched == "b"
