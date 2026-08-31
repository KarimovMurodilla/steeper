"""Report product events to Steeper, so the platform can build funnels.

Telegram traffic tells the platform that a user sent a message; it cannot tell
it that the user finished onboarding or paid. Those steps live inside the bot's
own code, and :class:`EventTracker` is how they get out — the bot calls
:meth:`SteeperMiddleware.track`, and the event is batched and shipped in the
background.

The shape mirrors :mod:`steeper._logging`, for the same reasons, with one
deliberate difference:

*No latency.* :meth:`EventTracker.track` only appends to a deque. A background
thread ships batches, so a handler never waits for the network — the same
guarantee everything else in this library makes.

*No unbounded memory.* The buffer is a bounded deque; once full, the **oldest**
events are dropped. That choice is not arbitrary. Losing a funnel's *entry*
events removes those users from the report entirely, which shrinks the window
but leaves the conversion rate roughly unbiased. Losing the *later* events of
users already counted at step one drags the numerator down and reports
conversion that never dropped as a drop. Dropping the oldest slice sheds whole
users; dropping the newest would manufacture false non-conversion.

*Ordering is the caller's clock.* An event is timestamped when ``track()`` is
called, never when it is flushed. The backend orders funnel steps by that
timestamp, so stamping at flush time would collapse a batch into one instant
and scramble every step order inside it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import deque
from typing import Any

from steeper._background import fire_and_forget_threadsafe, run_threadsafe
from steeper._config import SteeperConfig
from steeper._event_client import SteeperEventClient
from steeper._logging import _jsonable

logger = logging.getLogger("steeper")

#: Events held in memory while the backend is unreachable. Beyond this the
#: oldest are dropped — see the module docstring for why oldest.
MAX_BUFFERED = 10_000

#: Hard cap per request, mirroring the backend's own limit on a batch.
MAX_BATCH = 500

#: The backend stores the name in a ``String(128)`` column.
MAX_NAME_CHARS = 128

#: Caps on ``props``. The backend column is schemaless JSONB, so without a cap
#: here a bot could quietly turn its event log into a document store and take
#: the funnel queries down with it.
MAX_PROPS_KEYS = 50
MAX_PROPS_CHARS = 8_000


class EventTracker:
    """Buffers product events and ships them to Steeper in batches.

    Args:
        config: The Steeper configuration (backend URL, bot id, auth secret).
        batch_size: Events buffered before a batch is shipped early.
        flush_interval: Seconds between flushes of a partial batch.
        timeout: Per-request timeout for the shipping HTTP client.
    """

    def __init__(
        self,
        config: SteeperConfig,
        *,
        batch_size: int = 50,
        flush_interval: float = 5.0,
        timeout: float = 10.0,
    ) -> None:
        self._client = SteeperEventClient(config, timeout=timeout)
        self._batch_size = max(1, min(batch_size, MAX_BATCH))
        self._flush_interval = flush_interval

        self._buffer: deque[dict[str, Any]] = deque(maxlen=MAX_BUFFERED)
        self._buffer_lock = threading.Lock()
        self._dropped = 0
        self._drop_warned = False
        self._reject_warned = False

        self._wakeup = threading.Event()
        self._closing = threading.Event()
        self._flusher: threading.Thread | None = None
        # Guards the lazy thread start: track() may be called from several
        # handler threads at once on the very first event.
        self._start_lock = threading.Lock()

    # ----- Public API ----- #

    def track(
        self,
        name: str,
        *,
        user_id: int,
        props: dict[str, Any] | None = None,
        ts: float | None = None,
    ) -> None:
        """Record one product event. Never blocks, never raises.

        Args:
            name: Event name, matched verbatim against a funnel's steps. Keep it
                stable — renaming an event breaks every funnel built on it.
            user_id: Telegram id of the user the event belongs to. This is the
                raw ``from_user.id``, not any Steeper-side identifier.
            props: Optional structured context. Stored, but not used for funnel
                matching, and neither indexed nor searchable yet.
            ts: Unix timestamp; defaults to now. Pass it only when replaying an
                event whose real time differs from the call.
        """
        if self._closing.is_set():
            return

        payload = self._serialize(name, user_id, props, ts)
        if payload is None:
            return

        self._ensure_flusher()

        with self._buffer_lock:
            was_full = len(self._buffer) == MAX_BUFFERED
            self._buffer.append(payload)
            if was_full:
                self._dropped += 1
            should_flush = len(self._buffer) >= self._batch_size

        if should_flush:
            self._wakeup.set()

    def flush(self) -> None:
        """Ask the flusher to ship whatever is buffered right now."""
        self._wakeup.set()

    def close(self) -> None:
        """Stop the flusher, ship what is left, and close the HTTP client.

        Idempotent. Unlike log capture this flush is worth waiting for even on a
        hurried shutdown: the events still buffered are the most recent ones,
        which is exactly where a funnel's last step tends to live.
        """
        if self._closing.is_set():
            return
        self._closing.set()
        self._wakeup.set()

        flusher = self._flusher
        if flusher is not None:
            flusher.join(timeout=self._flush_interval + 5.0)

        # Whatever the flusher did not get to, ship synchronously — this is the
        # one place the caller does want to wait.
        for batch in self._drain():
            run_threadsafe(self._client.push(batch), timeout=self._client.timeout + 1.0)
        run_threadsafe(self._client.aclose(), timeout=5.0)

    async def aclose(self) -> None:
        """:meth:`close` for async callers.

        Run in a worker thread: closing flushes over the network, and doing that
        inline would block the bot's event loop until the final batches land.
        """
        if self._closing.is_set():
            return
        await asyncio.get_running_loop().run_in_executor(None, self.close)

    # ----- Internals ----- #

    def _ensure_flusher(self) -> None:
        """Start the flusher on the first event, not on construction.

        A bot that never calls ``track()`` should not pay for a thread it will
        never use, and every integration builds a tracker unconditionally.
        """
        if self._flusher is not None:
            return
        with self._start_lock:
            if self._flusher is not None:
                return
            flusher = threading.Thread(
                target=self._flush_loop,
                name="steeper-event-flusher",
                daemon=True,
            )
            self._flusher = flusher
            flusher.start()

    def _serialize(
        self,
        name: str,
        user_id: int,
        props: dict[str, Any] | None,
        ts: float | None,
    ) -> dict[str, Any] | None:
        """Validate and normalize one event, or return None to drop it."""
        if not isinstance(name, str) or not name.strip():
            self._reject("event name must be a non-empty string")
            return None

        clean_name = name.strip()
        if len(clean_name) > MAX_NAME_CHARS:
            self._reject(f"event name {clean_name[:40]!r}… exceeds {MAX_NAME_CHARS} characters")
            return None

        # bool is an int subclass, and True as a Telegram user id is a bug worth
        # surfacing rather than sending.
        if not isinstance(user_id, int) or isinstance(user_id, bool):
            self._reject(f"user_id must be an int, got {type(user_id).__name__}")
            return None

        return {
            "name": clean_name,
            "tg_user_id": user_id,
            # Stamped now, not at flush time: the backend orders funnel steps by
            # this value.
            "ts": time.time() if ts is None else float(ts),
            "props": self._clean_props(props),
        }

    def _clean_props(self, props: dict[str, Any] | None) -> dict[str, Any]:
        """Coerce props to JSON and clamp them, or give up and return nothing."""
        if not props:
            return {}
        if not isinstance(props, dict):
            self._reject(f"props must be a dict, got {type(props).__name__}")
            return {}

        clean = {str(key): _jsonable(value) for key, value in props.items()}

        if len(clean) > MAX_PROPS_KEYS:
            self._reject(f"props has {len(clean)} keys; keeping the first {MAX_PROPS_KEYS}")
            clean = dict(list(clean.items())[:MAX_PROPS_KEYS])

        try:
            encoded = json.dumps(clean)
        except (TypeError, ValueError):
            # _jsonable should have made this impossible; drop props rather
            # than lose the event, which still carries the name and the user.
            self._reject("props could not be serialized; dropping them")
            return {}

        if len(encoded) > MAX_PROPS_CHARS:
            self._reject(
                f"props serialize to {len(encoded)} characters, over the "
                f"{MAX_PROPS_CHARS} limit; dropping them"
            )
            return {}

        return clean

    def _reject(self, reason: str) -> None:
        """Report a malformed event once, loudly, then quietly.

        These are bugs in the calling code rather than runtime conditions, so
        the first one is a WARNING; repeating it for every call in a hot handler
        would be its own problem.
        """
        if not self._reject_warned:
            self._reject_warned = True
            logger.warning(
                "Steeper rejected an event: %s. Further rejections log at DEBUG.", reason
            )
        else:
            logger.debug("Steeper rejected an event: %s", reason)

    def _drain(self) -> list[list[dict[str, Any]]]:
        """Take everything buffered, split into request-sized batches."""
        with self._buffer_lock:
            if not self._buffer:
                return []
            events = list(self._buffer)
            self._buffer.clear()
            dropped, self._dropped = self._dropped, 0

        if dropped:
            self._report_drops(dropped)

        return [events[i : i + MAX_BATCH] for i in range(0, len(events), MAX_BATCH)]

    def _report_drops(self, dropped: int) -> None:
        """Warn once per outage that events are being lost."""
        if not self._drop_warned:
            self._drop_warned = True
            logger.warning(
                "Steeper event buffer is full (%d events); dropping the oldest. "
                "%d dropped so far. Funnels covering this period will undercount. "
                "Further drops log at DEBUG.",
                MAX_BUFFERED,
                dropped,
            )
        else:
            logger.debug("Steeper dropped %d buffered events", dropped)

    def _flush_loop(self) -> None:
        while not self._closing.is_set():
            self._wakeup.wait(self._flush_interval)
            self._wakeup.clear()
            if self._closing.is_set():
                return
            for batch in self._drain():
                # Shipping runs on the shared background loop: the flusher
                # thread has no event loop of its own, and one loop keeps the
                # HTTP client's connection pool bound to a single loop.
                fire_and_forget_threadsafe(self._client.push(batch))
            if not self._buffer:
                self._drop_warned = False
