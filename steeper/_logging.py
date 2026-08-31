"""Capture the host bot's ``logging`` output and ship it to Steeper.

The platform shows a bot's system logs next to its conversations, which means
the bot process has to hand its log records over. That is what
:class:`SteeperLogHandler` does — it is an ordinary ``logging.Handler`` you can
attach anywhere, and :meth:`SteeperMiddleware.setup` attaches it to the root
logger for you when ``capture_logs=True``.

Three properties matter more than anything else here:

*No recursion.* Shipping a log record makes HTTP calls, which themselves log.
Feeding those back into the handler would spiral, so records from ``steeper``
and its HTTP stack are dropped, and a thread-local guard breaks any remaining
cycle.

*No latency.* Log volume is orders of magnitude higher than update volume, so
records are batched and flushed from a background thread; ``emit`` only appends
to a deque. Nothing on the bot's own path ever waits for the network.

*No unbounded memory.* If the backend is down the buffer would otherwise grow
until the process dies. It is a bounded deque: once full, the **oldest** records
are dropped — for logs the newest ones are the interesting ones, the opposite of
the update forwarder's choice.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from steeper._background import fire_and_forget_threadsafe, run_threadsafe
from steeper._config import SteeperConfig
from steeper._log_client import SteeperLogClient

logger = logging.getLogger("steeper")

#: Loggers whose records are never shipped. Shipping them would log again from
#: inside the shipping path — an infinite loop that ends in a crash, not a
#: dropped record.
DEFAULT_EXCLUDED_LOGGERS: frozenset[str] = frozenset(
    {"steeper", "httpx", "httpcore", "hpack", "h11", "anyio"}
)

#: Records held in memory while the backend is unreachable. Beyond this the
#: oldest are dropped.
MAX_BUFFERED = 10_000

#: Hard cap per request, mirroring the backend's own limit on a batch.
MAX_BATCH = 500

#: Long values are truncated rather than dropped, mirroring the backend.
MAX_MESSAGE_CHARS = 20_000
MAX_EXC_CHARS = 50_000
_TRUNCATION_MARKER = "… [truncated]"

# Levels the backend accepts. A custom level (TRACE, VERBOSE, …) is reported as
# the nearest standard one below it, so an exotic level never fails the request.
_STANDARD_LEVELS: tuple[tuple[int, str], ...] = (
    (logging.CRITICAL, "CRITICAL"),
    (logging.ERROR, "ERROR"),
    (logging.WARNING, "WARNING"),
    (logging.INFO, "INFO"),
    (logging.DEBUG, "DEBUG"),
)

# Attributes every LogRecord carries. Anything else on the record was put there
# by the application (``logger.info(..., extra={...})``) and is worth shipping.
_RESERVED_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)

# Set while this thread is inside emit(), so a log emitted from the shipping
# path itself cannot re-enter and recurse.
_local = threading.local()


def _level_name(levelno: int) -> str:
    for threshold, name in _STANDARD_LEVELS:
        if levelno >= threshold:
            return name
    return "DEBUG"


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + _TRUNCATION_MARKER


def _clip(value: str | None, limit: int = 255) -> str | None:
    """Trim an optional identifier to the column width the backend accepts."""
    if not value:
        return None
    return value[:limit]


def _jsonable(value: Any) -> Any:
    """Coerce an extra value into something ``json`` can serialize."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return repr(value)


class SteeperLogHandler(logging.Handler):
    """A ``logging.Handler`` that batches records and ships them to Steeper.

    Args:
        config: The Steeper configuration (backend URL, bot id, auth secret).
        level: Minimum level to capture. ``DEBUG`` on a chatty bot can be a lot
            of traffic; ``INFO`` is the default for that reason.
        batch_size: Flush as soon as this many records are buffered.
        flush_interval: Flush at least this often, in seconds, so a quiet bot's
            records still show up promptly.
        timeout: HTTP timeout for a single batch.
        exclude_loggers: Logger name prefixes never shipped. Defaults to
            :data:`DEFAULT_EXCLUDED_LOGGERS`; anything passed here is added to
            those rather than replacing them, because dropping the built-ins
            would reintroduce the recursion they prevent.
    """

    def __init__(
        self,
        config: SteeperConfig,
        *,
        level: int | str = logging.INFO,
        batch_size: int = 100,
        flush_interval: float = 2.0,
        timeout: float = 10.0,
        exclude_loggers: frozenset[str] | set[str] | None = None,
    ) -> None:
        super().__init__(level=level)
        self._client = SteeperLogClient(config, timeout=timeout)
        self._batch_size = max(1, min(batch_size, MAX_BATCH))
        self._flush_interval = flush_interval
        self._excluded = DEFAULT_EXCLUDED_LOGGERS | frozenset(exclude_loggers or ())

        self._buffer: deque[dict[str, Any]] = deque(maxlen=MAX_BUFFERED)
        self._buffer_lock = threading.Lock()
        self._dropped = 0
        self._drop_warned = False

        self._wakeup = threading.Event()
        self._closing = threading.Event()
        self._flusher = threading.Thread(
            target=self._flush_loop,
            name="steeper-log-flusher",
            daemon=True,
        )
        self._flusher.start()

    # ----- logging.Handler API ----- #

    def emit(self, record: logging.LogRecord) -> None:
        """Buffer one record. Never blocks, never raises."""
        if self._is_excluded(record.name) or getattr(_local, "emitting", False):
            return

        _local.emitting = True
        try:
            payload = self._serialize(record)
        except Exception:
            # A record we cannot serialize is not worth crashing the caller's
            # logging call over.
            return
        finally:
            _local.emitting = False

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

        Called by ``logging.shutdown()`` at interpreter exit, and by the
        middleware when the bot stops.
        """
        if self._closing.is_set():
            super().close()
            return

        self._closing.set()
        self._wakeup.set()
        self._flusher.join(timeout=self._flush_interval + 5.0)

        # Whatever the flusher did not get to, ship synchronously — this is the
        # one place the caller does want to wait.
        pending = self._drain()
        for batch in pending:
            run_threadsafe(self._client.push(batch), timeout=self._client.timeout + 1.0)
        run_threadsafe(self._client.aclose(), timeout=5.0)

        super().close()

    # ----- Internals ----- #

    def _is_excluded(self, name: str) -> bool:
        return any(name == prefix or name.startswith(prefix + ".") for prefix in self._excluded)

    def _serialize(self, record: logging.LogRecord) -> dict[str, Any]:
        extra = {
            key: _jsonable(value)
            for key, value in record.__dict__.items()
            if key not in _RESERVED_RECORD_ATTRS and not key.startswith("_")
        }

        exc: str | None = None
        if record.exc_info:
            exc = _truncate(self.format_exception(record), MAX_EXC_CHARS)

        return {
            "ts": record.created,
            "level": _level_name(record.levelno),
            "logger": record.name[:255],
            "message": _truncate(record.getMessage(), MAX_MESSAGE_CHARS),
            "module": _clip(record.module),
            "func": _clip(record.funcName),
            "line": record.lineno,
            "exc": exc,
            "extra": extra,
        }

    def format_exception(self, record: logging.LogRecord) -> str:
        """Render ``exc_info`` the way ``logging`` would, without the message."""
        formatter = self.formatter or logging.Formatter()
        return formatter.formatException(record.exc_info)  # type: ignore[arg-type]

    def _drain(self) -> list[list[dict[str, Any]]]:
        """Take everything buffered, split into request-sized batches."""
        with self._buffer_lock:
            if not self._buffer:
                return []
            records = list(self._buffer)
            self._buffer.clear()
            dropped, self._dropped = self._dropped, 0

        if dropped:
            self._report_drops(dropped)

        return [records[i : i + MAX_BATCH] for i in range(0, len(records), MAX_BATCH)]

    def _report_drops(self, dropped: int) -> None:
        """Warn once per outage that log records are being lost."""
        if not self._drop_warned:
            self._drop_warned = True
            logger.warning(
                "Steeper log buffer is full (%d records); dropping the oldest. "
                "%d dropped so far. Further drops log at DEBUG.",
                MAX_BUFFERED,
                dropped,
            )
        else:
            logger.debug("Steeper dropped %d buffered log records", dropped)

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


def install_log_handler(
    config: SteeperConfig,
    *,
    level: int | str = logging.INFO,
    batch_size: int = 100,
    flush_interval: float = 2.0,
    timeout: float = 10.0,
    exclude_loggers: frozenset[str] | set[str] | None = None,
    target: logging.Logger | None = None,
) -> SteeperLogHandler:
    """Attach a :class:`SteeperLogHandler` to ``target`` (the root logger by default).

    The target logger's own level still applies: a root logger left at
    ``WARNING`` will never hand ``INFO`` records to any handler, so the level is
    lowered to the handler's when it is more restrictive.
    """
    target = target or logging.getLogger()
    handler = SteeperLogHandler(
        config,
        level=level,
        batch_size=batch_size,
        flush_interval=flush_interval,
        timeout=timeout,
        exclude_loggers=exclude_loggers,
    )
    if target.level == logging.NOTSET or target.level > handler.level:
        target.setLevel(handler.level)
    target.addHandler(handler)
    return handler


@dataclass(frozen=True, slots=True)
class LogCaptureOptions:
    """Log-capture settings, as accepted by every integration's constructor."""

    enabled: bool = False
    level: int | str = logging.INFO
    batch_size: int = 100
    flush_interval: float = 2.0
    exclude_loggers: frozenset[str] | None = None


@dataclass(slots=True)
class LogCapture:
    """Owns the handler's lifetime for an integration.

    The three integrations differ in how they hook into their framework but not
    in how they capture logs, so the start/stop dance lives here once.
    """

    options: LogCaptureOptions = field(default_factory=LogCaptureOptions)
    handler: SteeperLogHandler | None = None

    def start(self, config: SteeperConfig, *, timeout: float) -> None:
        """Attach the handler to the root logger, unless already attached."""
        if not self.options.enabled or self.handler is not None:
            return
        self.handler = install_log_handler(
            config,
            level=self.options.level,
            batch_size=self.options.batch_size,
            flush_interval=self.options.flush_interval,
            timeout=timeout,
            exclude_loggers=self.options.exclude_loggers,
        )

    def stop(self) -> None:
        """Detach the handler and ship whatever is still buffered."""
        handler = self.handler
        if handler is None:
            return
        self.handler = None
        logging.getLogger().removeHandler(handler)
        handler.close()

    async def astop(self) -> None:
        """:meth:`stop` for async callers.

        Closing flushes the buffer over the network, so it is run in a worker
        thread: doing it inline would block the bot's event loop for as long as
        the final batches take.
        """
        if self.handler is None:
            return
        await asyncio.get_running_loop().run_in_executor(None, self.stop)
