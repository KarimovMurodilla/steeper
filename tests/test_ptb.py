"""Tests for the python-telegram-bot integration.

The integration patches ``Bot._post`` at class level, keeps its state in module
globals, and chains onto the application's ``post_shutdown``; all three are
asserted here, and every test restores the patch state.
"""

import asyncio
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
import respx
from telegram import Bot, Chat, Message, Update
from telegram.ext import ApplicationBuilder

from steeper.integrations import ptb as integration
from steeper.integrations.ptb import (
    SteeperMiddleware,
    _chain_post_shutdown,
    _log_ptb_outgoing,
    _messages_from_ptb_post_result,
    _snapshot_from_ptb_message,
    _SteeperHandler,
)
from steeper.repository import OutgoingMessageSnapshot, SteeperRepository

BOT_ID = "d74d82b4-7c00-408d-b611-2411e0b3c6f8"
BOT_TOKEN = "123456:ABC-DEF"
BASE_URL = "https://api.example.com"

_MESSAGE_JSON = {
    "message_id": 7,
    "chat": {"id": 42, "type": "private"},
    "date": 1700000000,
    "text": "hello",
}


@pytest.fixture(autouse=True)
def _restore_patch_state() -> Iterator[None]:
    orig_post = Bot._post
    saved = integration._orig_bot_post
    yield
    Bot._post = orig_post  # type: ignore[method-assign]
    integration._orig_bot_post = saved
    integration._bot_repos.clear()
    integration._setup_applications.clear()


def _middleware() -> SteeperMiddleware:
    return SteeperMiddleware(base_url=BASE_URL, bot_id=BOT_ID, bot_token=BOT_TOKEN)


def _application() -> Any:
    return ApplicationBuilder().token(BOT_TOKEN).build()


def _message(**overrides: Any) -> Message:
    fields: dict[str, Any] = {
        "message_id": 7,
        "date": datetime.fromtimestamp(1700000000, tz=timezone.utc),
        "chat": Chat(id=42, type="private"),
        "text": "hello",
    }
    fields.update(overrides)
    return Message(**fields)


class _RecordingRepository:
    """Stands in for SteeperRepository; records instead of sending."""

    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []
        self.outgoing: list[OutgoingMessageSnapshot] = []

    async def forward_update(self, update: dict[str, Any]) -> None:
        self.updates.append(update)

    async def record_outgoing(self, snapshot: OutgoingMessageSnapshot) -> None:
        self.outgoing.append(snapshot)


def test_snapshot_uses_text_and_message_fields() -> None:
    assert _snapshot_from_ptb_message(_message()) == OutgoingMessageSnapshot(
        chat_id=42, message_id=7, text="hello", date=1700000000
    )


def test_snapshot_falls_back_to_caption() -> None:
    assert _snapshot_from_ptb_message(_message(text=None, caption="  a photo  ")).text == "a photo"


def test_decodes_a_single_message_response() -> None:
    messages = _messages_from_ptb_post_result(None, _MESSAGE_JSON)

    assert [m.message_id for m in messages] == [7]


def test_decodes_a_media_group_response() -> None:
    payload = [_MESSAGE_JSON, {**_MESSAGE_JSON, "message_id": 8}]

    messages = _messages_from_ptb_post_result(None, payload)

    assert [m.message_id for m in messages] == [7, 8]


@pytest.mark.parametrize(
    "result",
    [True, None, {"ok": True}, [], [{"not": "a message"}], "text"],
)
def test_responses_that_are_not_messages_decode_to_nothing(result: Any) -> None:
    assert _messages_from_ptb_post_result(None, result) == []


async def test_log_outgoing_records_every_message() -> None:
    repo = _RecordingRepository()

    await _log_ptb_outgoing(None, repo, [_MESSAGE_JSON, {**_MESSAGE_JSON, "message_id": 8}])  # type: ignore[arg-type]

    assert [s.message_id for s in repo.outgoing] == [7, 8]


def test_handler_accepts_updates_and_rejects_other_objects() -> None:
    handler = _SteeperHandler(_RecordingRepository())  # type: ignore[arg-type]

    assert handler.check_update(Update(update_id=1)) is True
    assert handler.check_update("not an update") is False


async def test_handler_forwards_the_full_update() -> None:
    repo = _RecordingRepository()
    handler = _SteeperHandler(repo)  # type: ignore[arg-type]
    update = Update(update_id=1, message=_message())

    await handler.handle_update(update, None, None, None)  # type: ignore[arg-type]
    await asyncio.sleep(0)

    assert repo.updates[0]["update_id"] == 1
    assert repo.updates[0]["message"]["text"] == "hello"


async def test_a_broken_update_payload_is_swallowed() -> None:
    repo = _RecordingRepository()
    handler = _SteeperHandler(repo)  # type: ignore[arg-type]

    class _Unserializable(Update):
        def to_dict(self, recursive: bool = True) -> dict[str, Any]:
            raise ValueError("nope")

    await handler.handle_update(_Unserializable(update_id=1), None, None, None)  # type: ignore[arg-type]

    assert repo.updates == []


async def test_setup_registers_a_low_priority_handler() -> None:
    app = _application()
    middleware = _middleware()

    middleware.setup(app)

    assert any(isinstance(h, _SteeperHandler) for h in app.handlers[-1])
    await middleware.aclose()


async def test_setup_is_idempotent() -> None:
    app = _application()
    middleware = _middleware()

    middleware.setup(app)
    wrapped_post = Bot._post
    handlers = sum(len(group) for group in app.handlers.values())

    middleware.setup(app)

    assert Bot._post is wrapped_post, "a second setup() must not nest another wrapper"
    assert sum(len(group) for group in app.handlers.values()) == handlers
    await middleware.aclose()


@respx.mock
async def test_outgoing_messages_are_logged() -> None:
    app = _application()
    middleware = _middleware()
    route = respx.post(middleware.repository.config.bot_message_url).mock(
        return_value=httpx.Response(200)
    )

    async def fake_post(self: Any, endpoint: str, data: Any = None, **kwargs: Any) -> Any:
        return _MESSAGE_JSON

    # Patch the class before setup() so the integration wraps this stub as its
    # original; PTB freezes instances, so `bot._post = ...` is not assignable.
    Bot._post = fake_post  # type: ignore[method-assign]
    middleware.setup(app)

    assert await app.bot._post("sendMessage", {}) == _MESSAGE_JSON
    for _ in range(5):
        await asyncio.sleep(0)

    assert route.called
    import json

    assert json.loads(route.calls.last.request.content)["message_id"] == 7
    await middleware.aclose()


async def test_post_shutdown_chain_runs_the_original_then_closes() -> None:
    app = _application()
    order: list[str] = []

    async def original(application: Any) -> None:
        order.append("original")

    app.post_shutdown = original

    async def close() -> None:
        order.append("close")

    _chain_post_shutdown(app, close)
    await app.post_shutdown(app)

    assert order == ["original", "close"]


async def test_post_shutdown_chain_works_without_an_original() -> None:
    app = _application()
    closed = False

    async def close() -> None:
        nonlocal closed
        closed = True

    _chain_post_shutdown(app, close)
    await app.post_shutdown(app)

    assert closed


async def test_setup_closes_the_client_on_post_shutdown() -> None:
    app = _application()
    middleware = _middleware()
    middleware.setup(app)

    await app.post_shutdown(app)

    assert middleware.client._http.is_closed


@respx.mock
async def test_aclose_closes_the_http_client() -> None:
    middleware = _middleware()
    respx.post(middleware.repository.config.webhook_url).mock(return_value=httpx.Response(200))
    await middleware.repository.forward_update({"update_id": 1})

    await middleware.aclose()

    assert middleware.client._http.is_closed


def test_repository_and_client_are_exposed() -> None:
    middleware = _middleware()

    assert isinstance(middleware.repository, SteeperRepository)
    assert middleware.client is middleware.repository.client
