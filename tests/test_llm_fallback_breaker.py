"""FallbackLLM circuit breaker: dead providers are skipped for a cool-down instead of costing a
failed round trip on every call, but the chain never refuses to try when all are cooling."""
import pytest

from app.models.llm import FallbackLLM


class HttpError(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status_code = status


class FakeModel:
    def __init__(self, name, error=None):
        self.model_name = name
        self.error = error
        self.calls = 0

    async def ainvoke(self, messages, config=None, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return f"answer from {self.model_name}"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


async def test_permanently_dead_model_is_tried_once_then_skipped():
    dead, ok = FakeModel("retired", HttpError(404)), FakeModel("good")
    chain = FallbackLLM([dead, ok], clock=Clock())

    assert await chain.ainvoke([]) == "answer from good"
    assert await chain.ainvoke([]) == "answer from good"
    assert await chain.ainvoke([]) == "answer from good"

    assert dead.calls == 1  # not retried on every call
    assert ok.calls == 3


@pytest.mark.parametrize("status", [401, 403, 404, 410])
async def test_all_permanent_statuses_get_the_long_cooldown(status):
    clock = Clock()
    dead, ok = FakeModel("dead", HttpError(status)), FakeModel("good")
    chain = FallbackLLM([dead, ok], clock=clock)
    await chain.ainvoke([])

    clock.now += FallbackLLM.PERMANENT_COOLDOWN_S - 1
    await chain.ainvoke([])
    assert dead.calls == 1  # still cooling

    clock.now += 2
    await chain.ainvoke([])
    assert dead.calls == 2  # cool-down over: probed again


async def test_transient_failure_gets_a_short_cooldown():
    clock = Clock()
    flaky, ok = FakeModel("flaky", HttpError(503)), FakeModel("good")
    chain = FallbackLLM([flaky, ok], clock=clock)
    await chain.ainvoke([])
    await chain.ainvoke([])
    assert flaky.calls == 1

    clock.now += FallbackLLM.TRANSIENT_COOLDOWN_S + 1
    await chain.ainvoke([])
    assert flaky.calls == 2


async def test_errors_without_a_status_are_treated_as_transient():
    clock = Clock()
    timeout, ok = FakeModel("slow", TimeoutError("timed out")), FakeModel("good")
    chain = FallbackLLM([timeout, ok], clock=clock)
    await chain.ainvoke([])
    clock.now += FallbackLLM.TRANSIENT_COOLDOWN_S + 1
    await chain.ainvoke([])
    assert timeout.calls == 2  # short cool-down only: a timeout is not a retired model


async def test_a_recovered_model_is_trusted_again():
    clock = Clock()
    model, ok = FakeModel("recovering", HttpError(503)), FakeModel("good")
    chain = FallbackLLM([model, ok], clock=clock)
    await chain.ainvoke([])
    clock.now += FallbackLLM.TRANSIENT_COOLDOWN_S + 1
    model.error = None
    assert await chain.ainvoke([]) == "answer from recovering"  # first in order again
    assert await chain.ainvoke([]) == "answer from recovering"


async def test_when_every_model_is_cooling_down_they_are_all_still_tried():
    a, b = FakeModel("a", HttpError(404)), FakeModel("b", HttpError(404))
    chain = FallbackLLM([a, b], clock=Clock())
    with pytest.raises(RuntimeError, match="All models failed"):
        await chain.ainvoke([])
    # Both are now cooling. A later call must not refuse outright: it tries them as a last resort.
    b.error = None
    assert await chain.ainvoke([]) == "answer from b"
    assert a.calls == 2 and b.calls == 2


async def test_healthy_models_are_preferred_over_cooling_ones():
    cooling, ok = FakeModel("cooling", HttpError(500)), FakeModel("ok")
    chain = FallbackLLM([cooling, ok], clock=Clock())
    await chain.ainvoke([])
    order = [m.model_name for m in chain._candidates()]
    assert order == ["ok", "cooling"]


class Reply:
    def __init__(self, content):
        self.content = content


class EmptyThenText(FakeModel):
    def __init__(self, name, replies):
        super().__init__(name)
        self.replies = list(replies)

    async def ainvoke(self, messages, config=None, **kwargs):
        self.calls += 1
        return Reply(self.replies.pop(0) if self.replies else "ok")


async def test_empty_reply_counts_as_a_failure_and_the_next_model_answers():
    empty, good = EmptyThenText("empty", [""]), EmptyThenText("good", ["a real answer"])
    chain = FallbackLLM([empty, good], clock=Clock())
    result = await chain.ainvoke([])
    assert result.content == "a real answer"
    assert empty.calls == 1 and good.calls == 1


async def test_whitespace_only_reply_is_empty_too():
    blank, good = EmptyThenText("blank", ["  \n\t "]), EmptyThenText("good", ["fine"])
    assert (await FallbackLLM([blank, good], clock=Clock()).ainvoke([])).content == "fine"


async def test_every_model_empty_raises_instead_of_returning_nothing():
    a, b = EmptyThenText("a", [""]), EmptyThenText("b", [""])
    with pytest.raises(RuntimeError, match="All models failed"):
        await FallbackLLM([a, b], clock=Clock()).ainvoke([])


async def test_non_text_content_is_not_mistaken_for_empty():
    class ListContent(FakeModel):
        async def ainvoke(self, messages, config=None, **kwargs):
            return Reply([{"type": "text", "text": "hi"}])

    assert (await FallbackLLM([ListContent("m")], clock=Clock()).ainvoke([])).content[0]["text"] == "hi"


async def test_cooling_models_are_ordered_soonest_recovery_first():
    clock = Clock()
    retired, flaky = FakeModel("retired", HttpError(404)), FakeModel("flaky", HttpError(503))
    chain = FallbackLLM([retired, flaky], clock=clock)
    with pytest.raises(RuntimeError):
        await chain.ainvoke([])
    # flaky recovers in 30s, retired only in 15 min: when all are cooling, probe flaky first
    assert [m.model_name for m in chain._candidates()] == ["flaky", "retired"]
