"""Tests for product-event tracking."""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import httpx
import pytest
import respx

from steeper._config import SteeperConfig
from steeper._event_client import SteeperEventClient
from steeper._events import (
    MAX_BUFFERED,
    MAX_NAME_CHARS,
    MAX_PROPS_CHARS,
    MAX_PROPS_KEYS,
    EventTracker,
)

BOT_ID = "d74d82b4-7c00-408d-b611-2411e0b3c6f8"
BOT_TOKEN = "123456:ABC-DEF"
BASE_URL = "https://api.example.com"
USER_ID = 123456789


def _config() -> SteeperConfig:
    return SteeperConfig(base_url=BASE_URL, bot_id=BOT_ID, bot_token=BOT_TOKEN)


class _CapturingTracker(EventTracker):
    """Tracker whose shipping is replaced by an in-memory sink.

    The flusher thread and the buffer stay real — they are what the tests are
    about — only the network call is stubbed out.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.shipped: list[list[dict[str, Any]]] = []
        self._shipped_event = threading.Event()
        super().__init__(_config(), **kwargs)

        async def fake_push(events: list[dict[str, Any]]) -> None:
            self.shipped.append(events)
            self._shipped_event.set()

        self._client.push = fake_push  # type: ignore[method-assign]

    def wait_for_shipment(self, timeout: float = 3.0) -> None:
        assert self._shipped_event.wait(timeout), "tracker never shipped a batch"
        self._shipped_event.clear()

    @property
    def flat(self) -> list[dict[str, Any]]:
        return [event for batch in self.shipped for event in batch]


def _tracker_without_flusher() -> _CapturingTracker:
    """A tracker whose flusher never starts, so the buffer can be inspected.

    ``batch_size`` is clamped to the backend's per-request maximum, so a large
    value cannot be used to keep the flusher idle: it would still drain every
    500 events. Handing the tracker an already-finished thread makes
    ``_ensure_flusher`` a no-op instead.
    """
    tracker = _CapturingTracker(batch_size=1, flush_interval=30.0)
    finished = threading.Thread(target=lambda: None)
    finished.start()
    finished.join()
    tracker._flusher = finished
    return tracker


# ----- Serialization ----- #


def test_serializes_the_fields_the_backend_expects() -> None:
    tracker = _CapturingTracker(batch_size=1)
    try:
        tracker.track("checkout_started", user_id=USER_ID, props={"plan": "pro"})
        tracker.wait_for_shipment()
    finally:
        tracker.close()

    event = tracker.flat[0]
    assert event["name"] == "checkout_started"
    assert event["tg_user_id"] == USER_ID
    assert event["props"] == {"plan": "pro"}
    assert isinstance(event["ts"], float)


def test_the_timestamp_is_the_moment_of_the_call_not_of_the_flush() -> None:
    # The backend orders funnel steps by this timestamp, so stamping at flush
    # time would collapse a batch into one instant and scramble step order.
    tracker = _CapturingTracker(batch_size=3, flush_interval=10.0)
    try:
        tracker.track("first", user_id=USER_ID)
        time.sleep(0.05)
        tracker.track("second", user_id=USER_ID)
        before_flush = time.time()
        time.sleep(0.05)
        tracker.track("third", user_id=USER_ID)
        tracker.wait_for_shipment()
    finally:
        tracker.close()

    events = {event["name"]: event["ts"] for event in tracker.flat}
    assert events["first"] < events["second"] < before_flush < events["third"]


def test_an_explicit_timestamp_is_kept() -> None:
    tracker = _CapturingTracker(batch_size=1)
    try:
        tracker.track("replayed", user_id=USER_ID, ts=1_700_000_000.5)
        tracker.wait_for_shipment()
    finally:
        tracker.close()

    assert tracker.flat[0]["ts"] == 1_700_000_000.5


def test_names_are_stripped_and_props_default_to_empty() -> None:
    tracker = _CapturingTracker(batch_size=1)
    try:
        tracker.track("  signup  ", user_id=USER_ID)
        tracker.wait_for_shipment()
    finally:
        tracker.close()

    assert tracker.flat[0]["name"] == "signup"
    assert tracker.flat[0]["props"] == {}


def test_props_are_coerced_to_json() -> None:
    class Opaque:
        def __repr__(self) -> str:
            return "<opaque>"

    tracker = _CapturingTracker(batch_size=1)
    try:
        tracker.track("paid", user_id=USER_ID, props={1: Opaque(), "ok": [1, "two"]})
        tracker.wait_for_shipment()
    finally:
        tracker.close()

    assert tracker.flat[0]["props"] == {"1": "<opaque>", "ok": [1, "two"]}


# ----- Rejection ----- #


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "", "user_id": USER_ID},
        {"name": "   ", "user_id": USER_ID},
        {"name": "x" * (MAX_NAME_CHARS + 1), "user_id": USER_ID},
        {"name": "ok", "user_id": "123"},
        # bool is an int subclass; True as a Telegram id is a bug, not an id.
        {"name": "ok", "user_id": True},
    ],
    ids=["empty", "blank", "too-long", "string-id", "bool-id"],
)
def test_malformed_events_are_dropped_not_raised(kwargs: dict[str, Any]) -> None:
    tracker = _CapturingTracker(batch_size=1, flush_interval=0.05)
    try:
        tracker.track(**kwargs)  # type: ignore[arg-type]
        time.sleep(0.2)
    finally:
        tracker.close()

    assert tracker.flat == []


def test_oversized_props_are_dropped_but_the_event_survives() -> None:
    # The name and the user are what a funnel needs; props are context.
    tracker = _CapturingTracker(batch_size=1)
    try:
        tracker.track("paid", user_id=USER_ID, props={"blob": "x" * (MAX_PROPS_CHARS + 100)})
        tracker.wait_for_shipment()
    finally:
        tracker.close()

    assert tracker.flat[0]["name"] == "paid"
    assert tracker.flat[0]["props"] == {}


def test_too_many_prop_keys_are_clipped() -> None:
    tracker = _CapturingTracker(batch_size=1)
    try:
        tracker.track(
            "paid",
            user_id=USER_ID,
            props={f"k{i}": i for i in range(MAX_PROPS_KEYS + 10)},
        )
        tracker.wait_for_shipment()
    finally:
        tracker.close()

    assert len(tracker.flat[0]["props"]) == MAX_PROPS_KEYS


def test_tracking_never_raises_on_a_broken_backend() -> None:
    tracker = EventTracker(_config(), batch_size=1, flush_interval=0.05, timeout=0.1)
    try:
        # Nothing is mocked, so the request fails; the caller must not notice.
        tracker.track("signup", user_id=USER_ID)
        time.sleep(0.3)
    finally:
        tracker.close()


# ----- Batching and bounded memory ----- #


def test_no_thread_is_started_until_the_first_event() -> None:
    # Every integration builds a tracker; a bot that never tracks should not
    # pay for a thread it will never use.
    tracker = _CapturingTracker(batch_size=1)
    try:
        assert tracker._flusher is None
        tracker.track("signup", user_id=USER_ID)
        assert tracker._flusher is not None
        tracker.wait_for_shipment()
    finally:
        tracker.close()


def test_a_full_batch_ships_before_the_interval_elapses() -> None:
    tracker = _CapturingTracker(batch_size=3, flush_interval=30.0)
    try:
        for i in range(3):
            tracker.track(f"step{i}", user_id=USER_ID)
        tracker.wait_for_shipment(timeout=3.0)
    finally:
        tracker.close()

    assert len(tracker.flat) == 3


def test_a_partial_batch_ships_on_the_interval() -> None:
    tracker = _CapturingTracker(batch_size=100, flush_interval=0.1)
    try:
        tracker.track("lonely", user_id=USER_ID)
        tracker.wait_for_shipment(timeout=3.0)
    finally:
        tracker.close()

    assert [event["name"] for event in tracker.flat] == ["lonely"]


def test_buffer_is_bounded_and_keeps_the_newest_events() -> None:
    # Dropping the oldest sheds whole users, which shrinks the window but keeps
    # the conversion rate roughly unbiased. Dropping the newest would delete
    # later steps of users already counted at step one, manufacturing
    # non-conversion that never happened.
    tracker = _tracker_without_flusher()
    try:
        for i in range(MAX_BUFFERED + 50):
            tracker.track(f"e{i}", user_id=USER_ID)

        assert len(tracker._buffer) == MAX_BUFFERED
        assert tracker._buffer[0]["name"] == "e50"
        assert tracker._buffer[-1]["name"] == f"e{MAX_BUFFERED + 49}"
        assert tracker._dropped == 50
    finally:
        tracker.close()


def test_a_full_buffer_warns_once_then_debugs(caplog: pytest.LogCaptureFixture) -> None:
    tracker = _tracker_without_flusher()
    try:
        for i in range(MAX_BUFFERED + 5):
            tracker.track(f"e{i}", user_id=USER_ID)

        with caplog.at_level(logging.WARNING, logger="steeper"):
            tracker._drain()
            tracker._dropped = 3
            tracker._drain()

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "dropping the oldest" in warnings[0].getMessage()
    finally:
        tracker.close()


def test_oversized_buffers_are_split_into_request_sized_batches() -> None:
    tracker = _tracker_without_flusher()
    try:
        for i in range(1200):
            tracker.track(f"e{i}", user_id=USER_ID)
        batches = tracker._drain()
    finally:
        tracker.close()

    assert [len(batch) for batch in batches] == [500, 500, 200]


# ----- Shutdown ----- #


def test_close_ships_what_is_still_buffered() -> None:
    tracker = _CapturingTracker(batch_size=100, flush_interval=30.0)
    tracker.track("last_gasp", user_id=USER_ID)

    tracker.close()

    assert [event["name"] for event in tracker.flat] == ["last_gasp"]


def test_close_is_idempotent() -> None:
    tracker = _CapturingTracker(batch_size=100, flush_interval=30.0)
    tracker.track("once", user_id=USER_ID)

    tracker.close()
    tracker.close()

    assert len(tracker.flat) == 1


def test_tracking_after_close_is_ignored() -> None:
    tracker = _CapturingTracker(batch_size=1)
    tracker.close()

    tracker.track("too_late", user_id=USER_ID)

    assert tracker.flat == []


async def test_aclose_ships_without_blocking_the_event_loop() -> None:
    tracker = _CapturingTracker(batch_size=100, flush_interval=30.0)
    tracker.track("async_gasp", user_id=USER_ID)

    await tracker.aclose()

    assert [event["name"] for event in tracker.flat] == ["async_gasp"]


# ----- HTTP contract ----- #


def test_events_url_is_the_webhook_endpoint_with_an_events_suffix() -> None:
    config = _config()

    assert config.events_url == f"{config.webhook_url}/events"


@respx.mock
async def test_push_posts_events_with_the_secret_header() -> None:
    config = _config()
    client = SteeperEventClient(config, timeout=1.0)
    route = respx.post(config.events_url).mock(return_value=httpx.Response(200))

    await client.push([{"name": "signup", "tg_user_id": USER_ID, "ts": 1.0, "props": {}}])

    request = route.calls.last.request
    assert request.headers["x-telegram-bot-api-secret-token"] == config.token_hash
    assert json.loads(request.content)["events"][0]["name"] == "signup"
    await client.aclose()


@respx.mock
async def test_push_never_raises_when_the_backend_fails() -> None:
    config = _config()
    client = SteeperEventClient(config, timeout=1.0)
    respx.post(config.events_url).mock(return_value=httpx.Response(500))

    await client.push([{"name": "signup", "tg_user_id": USER_ID, "ts": 1.0, "props": {}}])
    await client.aclose()


@respx.mock
async def test_push_of_an_empty_batch_makes_no_request() -> None:
    config = _config()
    client = SteeperEventClient(config, timeout=1.0)
    route = respx.post(config.events_url).mock(return_value=httpx.Response(200))

    await client.push([])

    assert not route.called
    await client.aclose()


@respx.mock
def test_end_to_end_a_tracked_event_reaches_the_backend() -> None:
    config = _config()
    route = respx.post(config.events_url).mock(return_value=httpx.Response(200))

    tracker = EventTracker(config, batch_size=1, timeout=1.0)
    try:
        tracker.track("payment_succeeded", user_id=USER_ID, props={"amount": 4900})
        deadline = time.time() + 3.0
        while not route.called and time.time() < deadline:
            time.sleep(0.05)
    finally:
        tracker.close()

    assert route.called
    payload = json.loads(route.calls.last.request.content)
    assert payload["events"][0]["name"] == "payment_succeeded"
    assert payload["events"][0]["tg_user_id"] == USER_ID
    assert payload["events"][0]["props"] == {"amount": 4900}


# ----- Integration surface ----- #


def test_every_integration_exposes_track_delegating_to_the_repository() -> None:
    # The three middlewares hook into their frameworks differently but must
    # offer the same tracking call, or a bot cannot switch frameworks without
    # rewriting its analytics.
    from steeper.integrations.aiogram import SteeperMiddleware as AiogramMiddleware
    from steeper.integrations.ptb import SteeperMiddleware as PTBMiddleware
    from steeper.integrations.telebot import SteeperMiddleware as TelebotMiddleware

    def _recording(sink: list[dict[str, Any]]) -> Any:
        def track(name: str, **kwargs: Any) -> None:
            sink.append({"name": name, **kwargs})

        return track

    for middleware_cls in (AiogramMiddleware, PTBMiddleware, TelebotMiddleware):
        middleware = middleware_cls(
            base_url=BASE_URL, bot_id=BOT_ID, bot_token=BOT_TOKEN, event_flush_interval=30.0
        )
        recorded: list[dict[str, Any]] = []
        middleware.tracker.track = _recording(recorded)  # type: ignore[method-assign]

        middleware.track("signup", user_id=USER_ID, props={"a": 1})

        assert recorded == [{"name": "signup", "user_id": USER_ID, "props": {"a": 1}, "ts": None}]


@respx.mock
async def test_repository_aclose_flushes_pending_events() -> None:
    # A conversion event lost at shutdown is a permanently wrong funnel number,
    # so closing has to wait for the buffer to drain.
    from steeper.repository import SteeperRepository

    config = _config()
    route = respx.post(config.events_url).mock(return_value=httpx.Response(200))
    respx.post(config.webhook_url).mock(return_value=httpx.Response(200))

    repository = SteeperRepository(
        base_url=BASE_URL,
        bot_id=BOT_ID,
        bot_token=BOT_TOKEN,
        event_flush_interval=30.0,
    )
    repository.track("payment_succeeded", user_id=USER_ID)

    await repository.aclose()

    assert route.called
    assert json.loads(route.calls.last.request.content)["events"][0]["name"] == (
        "payment_succeeded"
    )


@respx.mock
def test_telebot_close_flushes_events_synchronously() -> None:
    # telebot is synchronous and its close() bounds the whole call with a
    # timeout; the event flush is run before that so a slow final batch cannot
    # be abandoned by it.
    from steeper.integrations.telebot import SteeperMiddleware

    config = _config()
    route = respx.post(config.events_url).mock(return_value=httpx.Response(200))

    middleware = SteeperMiddleware(
        base_url=BASE_URL,
        bot_id=BOT_ID,
        bot_token=BOT_TOKEN,
        event_flush_interval=30.0,
    )
    middleware.track("paid", user_id=USER_ID)
    middleware.close(timeout=5.0)

    assert route.called
    assert json.loads(route.calls.last.request.content)["events"][0]["name"] == "paid"


def test_every_integration_exposes_the_tracker_it_actually_uses() -> None:
    # `middleware.tracker` is what handlers are told to depend on, so it has to
    # be the very object `track()` writes to — not a second one with its own
    # buffer and flush thread.
    from steeper.integrations.aiogram import SteeperMiddleware as AiogramMiddleware
    from steeper.integrations.ptb import SteeperMiddleware as PTBMiddleware
    from steeper.integrations.telebot import SteeperMiddleware as TelebotMiddleware

    for middleware_cls in (AiogramMiddleware, PTBMiddleware, TelebotMiddleware):
        middleware = middleware_cls(
            base_url=BASE_URL, bot_id=BOT_ID, bot_token=BOT_TOKEN, event_flush_interval=30.0
        )

        assert isinstance(middleware.tracker, EventTracker)
        assert middleware.tracker is middleware.repository.tracker
        # Stable across reads: handing it to a DI container must not hand out a
        # fresh tracker each time it is resolved.
        assert middleware.tracker is middleware.tracker


def test_a_handler_can_be_tested_with_a_fake_tracker() -> None:
    # The point of depending on the tracker rather than the middleware: no HTTP
    # client, no dispatcher, no setup().
    class FakeTracker:
        def __init__(self) -> None:
            self.events: list[tuple[str, int]] = []

        def track(self, name: str, *, user_id: int, **kwargs: Any) -> None:
            self.events.append((name, user_id))

    def buy(user_id: int, tracker: Any) -> None:
        tracker.track("checkout_started", user_id=user_id)

    tracker = FakeTracker()
    buy(42, tracker)

    assert tracker.events == [("checkout_started", 42)]
