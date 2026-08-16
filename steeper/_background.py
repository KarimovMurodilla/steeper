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

Both are also **bounded**. A backend that is slow or down means every forward
sits in flight for the full client timeout, so an unbounded scheduler would
accumulate one pending task per update until the process runs out of memory.
At most :data:`MAX_IN_FLIGHT` forwards may be in flight at once; beyond that
the *newest* work is dropped, which keeps the bot alive and bounds the damage
of an outage to the traffic recorded during it. Delivery is therefore
at-most-once — there is no retry and no persistent queue.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger("steeper")

#: Upper bound on forwards in flight at any moment, per scheduling strategy.
#: Reached only when the backend stops keeping up; see the module docstring.
MAX_IN_FLIGHT = 512

# Strong references keep pending tasks alive until they finish; the event
# loop itself only holds weak ones.
_tasks: set[asyncio.Task[Any]] = set()

# Drop bookkeeping, shared by both strategies. Guarded by a lock because the
# threadsafe path is called from arbitrary worker threads.
_drop_lock = threading.Lock()
_dropped_total = 0
_drop_warned = False


def _note_drop(reason: str) -> None:
    """Account for one dropped forward, warning once per outage.

    The first drop is worth a WARNING — it means Steeper is losing traffic.
    Every drop after that is DEBUG with a running total, because at this point
    they arrive as fast as the bot receives updates and a warning per drop
    would bury the host application's own logs.
    """
    global _dropped_total, _drop_warned
    with _drop_lock:
        _dropped_total += 1
        total = _dropped_total
        first = not _drop_warned
        _drop_warned = True
    if first:
        logger.warning(
            "Steeper has %d forwards in flight (the limit); dropping new ones until "
            "the backend keeps up. Reason: %s. Further drops log at DEBUG.",
            MAX_IN_FLIGHT,
            reason,
        )
    else:
        logger.debug("Steeper forward dropped (%s); %d dropped so far", reason, total)


def _note_drained() -> None:
    """Re-arm the warning once the queue empties, so a later outage warns again."""
    global _drop_warned
    if not _drop_warned:
        return
    with _drop_lock:
        _drop_warned = False


def _on_done(task: asyncio.Task[Any]) -> None:
    _tasks.discard(task)
    if not _tasks:
        _note_drained()
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.debug("Steeper forward failed", exc_info=exc)


def fire_and_forget(coro: Coroutine[Any, Any, Any]) -> None:
    """Run ``coro`` on the current event loop without awaiting it.

    Dropped if more than :data:`MAX_IN_FLIGHT` forwards are already pending.
    Failures are logged at DEBUG level and never propagate to the caller.
    """
    if len(_tasks) >= MAX_IN_FLIGHT:
        # Close the coroutine so it doesn't emit a "never awaited" warning.
        coro.close()
        _note_drop("in-flight limit reached")
        return
    try:
        task = asyncio.create_task(coro)
    except RuntimeError:
        # No running event loop — nothing sensible to do but drop the work.
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
        # Counted rather than tracked in a set: these run on another loop, and
        # a plain int under the existing lock is enough to enforce the cap.
        self._in_flight = 0

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
        """Schedule ``coro`` on the background loop without waiting for it.

        Dropped if the loop already has :data:`MAX_IN_FLIGHT` forwards pending.
        """
        with self._lock:
            if self._in_flight >= MAX_IN_FLIGHT:
                over_limit = True
            else:
                over_limit = False
                self._in_flight += 1
        if over_limit:
            coro.close()
            _note_drop("in-flight limit reached")
            return

        try:
            loop = self._ensure_loop()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception:
            # Never let scheduling failures break the bot's own call.
            self._release()
            logger.debug("Failed to schedule Steeper forward", exc_info=True)
            return

        def _retrieve(fut: concurrent.futures.Future[Any]) -> None:
            # Retrieve the result so exceptions are swallowed-and-logged here
            # instead of surfacing as "exception was never retrieved" warnings.
            try:
                fut.result()
            except Exception:
                logger.debug("Steeper forward failed", exc_info=True)
            finally:
                self._release()

        future.add_done_callback(_retrieve)

    def _release(self) -> None:
        with self._lock:
            self._in_flight -= 1
            drained = self._in_flight == 0
        if drained:
            _note_drained()

    def submit_sync(self, coro: Coroutine[Any, Any, Any], *, timeout: float) -> None:
        """Run ``coro`` on the background loop and wait for it to finish.

        Needed for shutdown from a synchronous framework: the ``AsyncClient`` is
        bound to this loop, so it cannot be closed from the calling thread, and
        unlike a forward the caller does need it to complete. Not subject to the
        in-flight cap — shutdown must not be dropped.
        """
        try:
            loop = self._ensure_loop()
            asyncio.run_coroutine_threadsafe(coro, loop).result(timeout)
        except Exception:
            # Closing is best-effort; a failure here must not break the caller.
            logger.debug("Steeper shutdown on the background loop failed", exc_info=True)


_background_loop = BackgroundLoop()


def fire_and_forget_threadsafe(coro: Coroutine[Any, Any, Any]) -> None:
    """Run ``coro`` on the shared background loop from any (sync) thread.

    Dropped if more than :data:`MAX_IN_FLIGHT` forwards are already pending.
    Failures are logged at DEBUG level and never propagate to the caller.
    """
    _background_loop.submit(coro)


def run_threadsafe(coro: Coroutine[Any, Any, Any], *, timeout: float = 5.0) -> None:
    """Run ``coro`` on the shared background loop and wait for it, from any thread.

    The blocking counterpart of :func:`fire_and_forget_threadsafe`, for shutdown.
    """
    _background_loop.submit_sync(coro, timeout=timeout)
