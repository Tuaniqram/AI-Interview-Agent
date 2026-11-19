"""The rate limiter must key on the real client behind a proxy, and must not grow without bound."""
import time

from app.middleware.rate_limit import RateLimitMiddleware


def _scope(peer="10.0.0.1", xff=None, path="/api/v1/auth/login"):
    headers = [(b"x-forwarded-for", xff.encode())] if xff is not None else []
    return {"type": "http", "path": path, "client": (peer, 1234), "headers": headers}


async def _call(mw, scope):
    """Returns the status the limiter let through (200) or answered (429)."""
    sent = []

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        sent.append(message)

    await mw(scope, receive, send)
    return next((m["status"] for m in sent if m["type"] == "http.response.start"), 200)


async def _ok_app(scope, receive, send):
    return None


def _mw(**kw):
    return RateLimitMiddleware(_ok_app, max_requests=2, window_seconds=60, **kw)


async def test_default_keys_on_the_socket_peer_so_a_proxy_is_one_bucket():
    mw = _mw()  # trusted_proxies=0: behaviour unchanged
    for who in ("1.1.1.1", "2.2.2.2"):
        await _call(mw, _scope(xff=who))
    # both "users" were the same proxy peer, so the third request from anyone is refused
    assert await _call(mw, _scope(xff="3.3.3.3")) == 429


async def test_behind_one_trusted_proxy_each_client_has_its_own_bucket():
    mw = _mw(trusted_proxies=1)
    for _ in range(2):
        assert await _call(mw, _scope(xff="1.1.1.1")) == 200
    assert await _call(mw, _scope(xff="1.1.1.1")) == 429  # that client is limited
    assert await _call(mw, _scope(xff="2.2.2.2")) == 200  # another client is not


async def test_forged_left_entries_cannot_pick_a_bucket():
    mw = _mw(trusted_proxies=1)
    # the attacker prepends fake addresses; the proxy appends the real one on the right
    for fake in ("9.9.9.1", "9.9.9.2"):
        assert await _call(mw, _scope(xff=f"{fake}, 7.7.7.7")) == 200
    assert await _call(mw, _scope(xff="9.9.9.3, 7.7.7.7")) == 429


async def test_two_trusted_proxies_use_the_second_from_the_right():
    mw = _mw(trusted_proxies=2)
    for _ in range(2):
        await _call(mw, _scope(xff="5.5.5.5, 192.168.0.9"))
    assert await _call(mw, _scope(xff="5.5.5.5, 192.168.0.10")) == 429


async def test_header_shorter_than_the_proxy_chain_falls_back_to_the_peer():
    mw = _mw(trusted_proxies=2)
    for _ in range(2):
        await _call(mw, _scope(peer="10.0.0.1", xff="1.1.1.1"))
    assert await _call(mw, _scope(peer="10.0.0.1", xff="2.2.2.2")) == 429


async def test_missing_header_with_trusted_proxies_falls_back_to_the_peer():
    mw = _mw(trusted_proxies=1)
    for _ in range(2):
        await _call(mw, _scope(peer="10.0.0.1"))
    assert await _call(mw, _scope(peer="10.0.0.1")) == 429


def test_idle_addresses_are_pruned():
    mw = _mw()
    now = time.time()
    mw._buckets["old"] = [now - 120]
    mw._buckets["empty"] = []
    mw._buckets["recent"] = [now - 5]
    mw._prune(now)
    assert set(mw._buckets) == {"recent"}


async def test_table_is_pruned_during_traffic():
    mw = _mw()
    now = time.time()
    for i in range(50):
        mw._buckets[f"stale-{i}"] = [now - 600]
    mw._since_prune = 1023  # the next request triggers the periodic prune
    await _call(mw, _scope(peer="10.0.0.1"))
    assert not any(k.startswith("stale-") for k in mw._buckets)
