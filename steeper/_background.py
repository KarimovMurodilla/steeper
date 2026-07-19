"""Fire-and-forget task scheduling for the integrations.

Forwarding to Steeper must never add latency to the host bot: awaiting the
HTTP round-trip inline would stall every incoming update and every outgoing
API call for up to the full client timeout whenever the backend is slow or
unreachable.

Two strategies cover the two kinds of host framework:

- :func:`fire_and_forget` — for async frameworks (aiogram, PTB) where a
  running event loop already exists; schedules the coroutine on it.
- :func:`fire_and_forget_threadsafe` — for sync frameworks (telebot) whose
  handlers run on plain worker threads with no event loop; schedules the
  coroutine on a shared long-lived background loop in a daemon thread.

Both share the same contract: never block the caller, never raise, log
failures at DEBUG.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger("steeper")

# Strong references keep pending tasks alive until they finish; the event
# loop itself only holds weak ones.
_tasks: set[asyncio.Task[Any]] = set()


def _on_done(task: asyncio.Task[Any]) -> None:
    _tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.debug("Steeper forward failed", exc_info=exc)


def fire_and_forget(coro: Coroutine[Any, Any, Any]) -> None:
    """Run ``coro`` on the current event loop without awaiting it.

    Failures are logged at DEBUG level and never propagate to the caller.
    """
    try:
        task = asyncio.create_task(coro)
    except RuntimeError:
        # No running event loop — nothing sensible to do but drop the work.
        # Close the coroutine so it doesn't emit a "never awaited" warning.
        coro.close()
        logger.debug("No running event loop; Steeper forward dropped", exc_info=True)
        return
    _tasks.add(task)
    task.add_done_callback(_on_done)


class BackgroundLoop:
    """A single daemon thread running an asyncio loop for fire-and-forget work.

    Sync frameworks dispatch handlers and API calls on worker threads that have
    no running event loop. Rather than block each call with ``asyncio.run``
    (which would stall the bot for the full Steeper round-trip and spin up a
    fresh loop every time), we run all forwarding on one long-lived background
    loop. This keeps the bot responsive even when the backend is slow or
    unreachable, and lets the ``httpx.AsyncClient`` stay bound to a single
    stable loop.
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None:
            return self._loop
        with self._lock:
            loop = self._loop
            if loop is None:
                loop = asyncio.new_event_loop()
                thread = threading.Thread(
                    target=loop.run_forever,
                    name="steeper-background",
                    daemon=True,
                )
                thread.start()
                self._loop = loop
            return loop

    def submit(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Schedule ``coro`` on the background loop without waiting for it."""
        try:
            loop = self._ensure_loop()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception:
            # Never let scheduling failures break the bot's own call.
            logger.debug("Failed to schedule Steeper forward", exc_info=True)
            return

        def _retrieve(fut: concurrent.futures.Future[Any]) -> None:
            # Retrieve the result so exceptions are swallowed-and-logged here
            # instead of surfacing as "exception was never retrieved" warnings.
            try:
                fut.result()
            except Exception:
                logger.debug("Steeper forward failed", exc_info=True)

        future.add_done_callback(_retrieve)


_background_loop = BackgroundLoop()


def fire_and_forget_threadsafe(coro: Coroutine[Any, Any, Any]) -> None:
    """Run ``coro`` on the shared background loop from any (sync) thread.

    Failures are logged at DEBUG level and never propagate to the caller.
    """
    _background_loop.submit(coro)
