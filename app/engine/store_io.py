"""Async-safe access to the session store.

``MemoryV4SessionStore`` / ``RedisV4SessionStore`` use *synchronous* database and Redis
clients (hydrate on a cache miss, durable checkpoint after every turn). Called directly from
async code, each of those calls freezes the whole event loop, and with it every other
interview and HTTP request, for the length of a (remote) database round trip. These helpers
run the blocking calls on a worker thread instead.
"""
import asyncio
from typing import Any


async def store_get(store, session_id: str) -> Any:
    return await asyncio.to_thread(store.get, session_id)


async def store_get_or_raise(store, session_id: str) -> Any:
    return await asyncio.to_thread(store.get_or_raise, session_id)


async def store_set(store, session_id: str, state: dict) -> Any:
    return await asyncio.to_thread(store.set, session_id, state)


async def store_checkpoint(store, session_id: str, state: dict) -> None:
    await asyncio.to_thread(store.checkpoint, session_id, state)


async def store_commit(store, session_id: str, brain) -> None:
    """Write a turn: the shared state first, then the durable checkpoint.

    A versioned store returns the new version, which the brain keeps so its next write is compared
    against this one. ``StaleSessionError`` (another worker wrote first) propagates: the turn is
    lost, never merged over a newer one.
    """
    version = await store_set(store, session_id, brain.to_dict())
    if isinstance(version, int):
        brain.store_version = version
    await store_checkpoint(store, session_id, brain.to_dict())
