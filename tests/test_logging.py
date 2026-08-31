"""Log capture: serialization, recursion safety, batching, and bounded memory.

The handler runs on the host bot's own logging path, so the properties pinned
here are the ones whose absence would take a bot down: it must never recurse
into itself, never raise into the caller's ``logger.info(...)``, and never grow
without a bound while the backend is unreachable.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import httpx
import pytest
import respx

from steeper import SteeperConfig
from steeper._log_client import SteeperLogClient
from steeper._logging import (
    MAX_BATCH,
    MAX_BUFFERED,
    LogCapture,
    LogCaptureOptions,
    SteeperLogHandler,
    install_log_handler,
)

BOT_ID = "d74d82b4-7c00-408d-b611-2411e0b3c6f8"
BOT_TOKEN = "123456:ABC-DEF"
BASE_URL = "https://api.example.com"


def _config() -> SteeperConfig:
    return SteeperConfig(base_url=BASE_URL, bot_id=BOT_ID, bot_token=BOT_TOKEN)


class _CapturingHandler(SteeperLogHandler):
    """Handler whose shipping is replaced by an in-memory sink.

    The flusher thread and the buffer stay real — they are what the tests are
    about — only the network call is stubbed out.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.shipped: list[list[dict[str, Any]]] = []
        self._shipped_event = threading.Event()
        super().__init__(_config(), **kwargs)

        async def fake_push(records: list[dict[str, Any]]) -> None:
            self.shipped.append(records)
            self._shipped_event.set()

        self._client.push = fake_push  # type: ignore[method-assign]

    def wait_for_shipment(self, timeout: float = 3.0) -> None:
        assert self._shipped_event.wait(timeout), "handler never shipped a batch"
        self._shipped_event.clear()


def _record(
    name: str = "app.handlers",
    level: int = logging.ERROR,
    msg: str = "Boom %s",
    args: tuple[Any, ...] = ("now",),
    **extra: Any,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="/app/handlers.py",
        lineno=42,
        msg=msg,
        args=args,
        exc_info=None,
        func="cmd_start",
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


# ----- Serialization ----- #


def test_serializes_the_fields_the_backend_expects() -> None:
    handler = _CapturingHandler(batch_size=1)
    try:
        payload = handler._serialize(_record(chat_id=1))
    finally:
        handler.close()

    assert payload["level"] == "ERROR"
    assert payload["logger"] == "app.handlers"
    assert payload["message"] == "Boom now"
    assert payload["func"] == "cmd_start"
    assert payload["line"] == 42
    assert payload["exc"] is None
    assert payload["extra"]["chat_id"] == 1
    assert isinstance(payload["ts"], float)


def test_custom_levels_map_to_the_nearest_standard_one() -> None:
    """The backend's enum has five levels; a custom one must not break ingest."""
    handler = _CapturingHandler(batch_size=1, level=1)
    try:
        assert handler._serialize(_record(level=25))["level"] == "INFO"
        assert handler._serialize(_record(level=logging.CRITICAL + 10))["level"] == "CRITICAL"
        assert handler._serialize(_record(level=1))["level"] == "DEBUG"
    finally:
        handler.close()


def test_exception_info_is_rendered_into_exc() -> None:
    handler = _CapturingHandler(batch_size=1)
    try:
        try:
            raise ValueError("kaboom")
        except ValueError:
            import sys

            record = _record()
            record.exc_info = sys.exc_info()
            payload = handler._serialize(record)
    finally:
        handler.close()

    assert payload["exc"] is not None
    assert "ValueError: kaboom" in payload["exc"]


def test_unserializable_extras_fall_back_to_repr() -> None:
    handler = _CapturingHandler(batch_size=1)

    class Weird:
        def __repr__(self) -> str:
            return "<weird>"

    try:
        payload = handler._serialize(_record(obj=Weird()))
    finally:
        handler.close()

    assert payload["extra"]["obj"] == "<weird>"
    # Whatever comes out must survive the trip to the backend.
    json.dumps(payload)


def test_oversized_values_are_truncated_not_dropped() -> None:
    handler = _CapturingHandler(batch_size=1)
    try:
        payload = handler._serialize(_record(msg="x" * 30_000, args=()))
    finally:
        handler.close()

    assert payload["message"].endswith("[truncated]")
    assert len(payload["message"]) < 30_000


def test_a_record_that_cannot_be_formatted_is_skipped_silently() -> None:
    """``logger.info("%d", "nope")`` must not raise out of the caller's call."""
    handler = _CapturingHandler(batch_size=1)
    try:
        handler.emit(_record(msg="%d", args=("not-a-number",)))
        assert len(handler._buffer) == 0
    finally:
        handler.close()


# ----- Recursion safety ----- #


@pytest.mark.parametrize(
    "name",
    ["steeper", "steeper.aiogram", "httpx", "httpcore.connection", "h11"],
)
def test_own_and_http_stack_records_are_never_shipped(name: str) -> None:
    """Shipping these would log from inside shipping — an endless loop."""
    handler = _CapturingHandler(batch_size=1)
    try:
        handler.emit(_record(name=name))
        assert len(handler._buffer) == 0
    finally:
        handler.close()


def test_extra_exclusions_are_added_to_the_builtin_ones() -> None:
    handler = _CapturingHandler(batch_size=1, exclude_loggers={"noisy"})
    try:
        handler.emit(_record(name="noisy.sub"))
        handler.emit(_record(name="httpx"))
        handler.emit(_record(name="app"))
        assert [r["logger"] for r in handler._buffer] == ["app"]
    finally:
        handler.close()


def test_logging_from_within_emit_does_not_recurse() -> None:
    handler = _CapturingHandler(batch_size=1000, flush_interval=60.0)
    reentered: list[int] = []

    original = handler._serialize

    def serialize_and_log(record: logging.LogRecord) -> dict[str, Any]:
        reentered.append(1)
        if len(reentered) < 5:
            # A third-party logger emitting from inside our own emit path.
            handler.emit(_record(name="third.party"))
        return original(record)

    handler._serialize = serialize_and_log  # type: ignore[method-assign]
    try:
        handler.emit(_record(name="app"))
        # Without the re-entrancy guard this recurses until the stack blows.
        assert len(reentered) == 1
    finally:
        handler._serialize = original  # type: ignore[method-assign]
        handler.close()


# ----- Batching and buffering ----- #


def test_full_batch_is_shipped_without_waiting_for_the_interval() -> None:
    handler = _CapturingHandler(batch_size=3, flush_interval=60.0)
    try:
        for _ in range(3):
            handler.emit(_record())
        handler.wait_for_shipment()
    finally:
        handler.close()

    assert sum(len(batch) for batch in handler.shipped) == 3


def test_partial_batch_is_shipped_on_the_interval() -> None:
    handler = _CapturingHandler(batch_size=100, flush_interval=0.05)
    try:
        handler.emit(_record())
        handler.wait_for_shipment()
    finally:
        handler.close()

    assert handler.shipped[0][0]["message"] == "Boom now"


def test_batch_size_is_clamped_to_the_backends_limit() -> None:
    handler = _CapturingHandler(batch_size=100_000)
    try:
        assert handler._batch_size == MAX_BATCH
    finally:
        handler.close()


def test_buffer_is_bounded_and_keeps_the_newest_records() -> None:
    """An unreachable backend must not be able to grow the bot's memory."""
    handler = _CapturingHandler(flush_interval=60.0)
    # Stop the flusher so nothing drains the buffer mid-test; this is the
    # "backend is gone, records keep coming" case.
    handler._closing.set()
    handler._wakeup.set()
    handler._flusher.join(timeout=3.0)
    try:
        for i in range(MAX_BUFFERED + 50):
            handler.emit(_record(msg=str(i), args=()))

        assert len(handler._buffer) == MAX_BUFFERED
        # Oldest dropped: for logs the newest records are the interesting ones.
        assert handler._buffer[-1]["message"] == str(MAX_BUFFERED + 49)
        assert handler._dropped == 50
    finally:
        handler.close()


def test_close_ships_what_is_still_buffered() -> None:
    handler = _CapturingHandler(batch_size=1000, flush_interval=60.0)
    handler.emit(_record(msg="last one", args=()))

    handler.close()

    assert [r["message"] for batch in handler.shipped for r in batch] == ["last one"]


def test_close_is_idempotent() -> None:
    handler = _CapturingHandler(batch_size=1)
    handler.close()
    handler.close()


# ----- Installation ----- #


def test_install_lowers_a_too_restrictive_root_level() -> None:
    root = logging.getLogger()
    original = root.level
    root.setLevel(logging.WARNING)

    handler = install_log_handler(_config(), level=logging.INFO)
    try:
        # A root logger left at WARNING would never hand INFO to any handler.
        assert root.level == logging.INFO
        assert handler in root.handlers
    finally:
        root.removeHandler(handler)
        handler.close()
        root.setLevel(original)


def test_capture_is_off_by_default_and_stop_detaches() -> None:
    root = logging.getLogger()
    before = list(root.handlers)

    capture = LogCapture(LogCaptureOptions())
    capture.start(_config(), timeout=1.0)
    assert list(root.handlers) == before

    capture = LogCapture(LogCaptureOptions(enabled=True))
    capture.start(_config(), timeout=1.0)
    assert len(root.handlers) == len(before) + 1
    capture.stop()
    assert list(root.handlers) == before


def test_start_twice_attaches_one_handler() -> None:
    root = logging.getLogger()
    before = list(root.handlers)

    capture = LogCapture(LogCaptureOptions(enabled=True))
    capture.start(_config(), timeout=1.0)
    capture.start(_config(), timeout=1.0)
    try:
        assert len(root.handlers) == len(before) + 1
    finally:
        capture.stop()


# ----- HTTP contract ----- #


@respx.mock
async def test_push_posts_records_with_the_secret_header() -> None:
    config = _config()
    client = SteeperLogClient(config, timeout=1.0)
    route = respx.post(config.logs_url).mock(return_value=httpx.Response(200))

    await client.push([{"ts": 1.0, "level": "INFO", "logger": "app", "message": "hi"}])

    request = route.calls.last.request
    assert request.headers["x-telegram-bot-api-secret-token"] == config.token_hash
    assert json.loads(request.content)["records"][0]["message"] == "hi"
    await client.aclose()


@respx.mock
async def test_push_never_raises_when_the_backend_fails() -> None:
    config = _config()
    client = SteeperLogClient(config, timeout=1.0)
    respx.post(config.logs_url).mock(return_value=httpx.Response(500))

    await client.push([{"ts": 1.0, "level": "INFO", "logger": "app", "message": "hi"}])
    await client.aclose()


@respx.mock
async def test_push_of_an_empty_batch_makes_no_request() -> None:
    config = _config()
    client = SteeperLogClient(config, timeout=1.0)
    route = respx.post(config.logs_url).mock(return_value=httpx.Response(200))

    await client.push([])

    assert not route.called
    await client.aclose()


def test_logs_url_is_the_webhook_endpoint_with_a_logs_suffix() -> None:
    config = _config()

    assert config.logs_url == f"{config.webhook_url}/logs"


@respx.mock
def test_end_to_end_a_logged_record_reaches_the_backend() -> None:
    config = _config()
    route = respx.post(config.logs_url).mock(return_value=httpx.Response(200))

    handler = SteeperLogHandler(config, level=logging.INFO, batch_size=1, timeout=1.0)
    app_logger = logging.getLogger("app.e2e")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(handler)
    try:
        app_logger.info("hello backend")
        deadline = time.time() + 3.0
        while not route.called and time.time() < deadline:
            time.sleep(0.05)
    finally:
        app_logger.removeHandler(handler)
        handler.close()

    assert route.called
    payload = json.loads(route.calls.last.request.content)
    assert payload["records"][0]["message"] == "hello backend"
    assert payload["records"][0]["logger"] == "app.e2e"
