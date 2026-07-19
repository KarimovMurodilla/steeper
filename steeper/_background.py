"""Fire-and-forget task scheduling for the async integrations.

Forwarding to Steeper must never add latency to the host bot: awaiting the
HTTP round-trip inline would stall every incoming update and every outgoing
API call for up to the full client timeout whenever the backend is slow or
unreachable.
"""

from __future__ import annotations

import asyncio
import logging
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
