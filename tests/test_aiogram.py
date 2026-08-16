"""Tests for the aiogram integration.

The integration patches ``Bot.__call__`` at class level and keeps its state in
module globals, so every test restores both.
"""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
import respx
from aiogram import Bot, Dispatcher
from aiogram.types import Chat, Message, Update

from steeper.integrations import aiogram as integration
from steeper.integrations.aiogram import (
    SteeperMiddleware,
    _IncomingMiddleware,
    _log_aiogram_outgoing,
    _snapshot_from_aiogram_message,
)
from steeper.repository import OutgoingMessageSnapshot, SteeperRepository

BOT_ID = "d74d82b4-7c00-408d-b611-2411e0b3c6f8"
BOT_TOKEN = "123456:ABC-DEF"
BASE_URL = "https://api.example.com"


@pytest.fixture(autouse=True)
def _restore_patch_state() -> Iterator[None]:
    orig_call = Bot.__call__
    saved = integration._orig_bot_call
    yield
    Bot.__call__ = orig_call  # type: ignore[method-assign]
    integration._orig_bot_call = saved
    integration._bot_repos.clear()


def _middleware() -> SteeperMiddleware:
    return SteeperMiddleware(base_url=BASE_URL, bot_id=BOT_ID, bot_token=BOT_TOKEN)


def _message(**overrides: Any) -> Message:
    fields: dict[str, Any] = {
        "message_id": 7,
        "date": datetime.fromtimestamp(1700000000, tz=timezone.utc),
        "chat": Chat(id=42, type="private"),
        "text": "hello",
    }
    fields.update(overrides)
    return Message.model_validate(fields)


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
    snapshot = _snapshot_from_aiogram_message(_message())

    assert snapshot == OutgoingMessageSnapshot(
        chat_id=42, message_id=7, text="hello", date=1700000000
    )


def test_snapshot_falls_back_to_caption() -> None:
    snapshot = _snapshot_from_aiogram_message(_message(text=None, caption="  a photo  "))

    assert snapshot.text == "a photo"


def test_snapshot_of_a_message_without_text_or_caption_is_empty() -> None:
    assert _snapshot_from_aiogram_message(_message(text=None)).text == ""


async def test_logs_a_single_message_result() -> None:
    repo = _RecordingRepository()

    await _log_aiogram_outgoing(repo, _message())  # type: ignore[arg-type]

    assert [s.message_id for s in repo.outgoing] == [7]


async def test_logs_every_message_of_a_media_group() -> None:
    repo = _RecordingRepository()
    group = [_message(message_id=1), _message(message_id=2)]

    await _log_aiogram_outgoing(repo, group)  # type: ignore[arg-type]

    assert [s.message_id for s in repo.outgoing] == [1, 2]


@pytest.mark.parametrize("result", [True, None, 42, [], ["not a message"]])
async def test_ignores_results_that_are_not_messages(result: Any) -> None:
    repo = _RecordingRepository()

    await _log_aiogram_outgoing(repo, result)  # type: ignore[arg-type]

    assert repo.outgoing == []


async def test_incoming_middleware_forwards_and_still_calls_the_handler() -> None:
    repo = _RecordingRepository()
    middleware = _IncomingMiddleware(repo)  # type: ignore[arg-type]
    update = Update(update_id=1, message=_message())
    called = False

    async def handler(event: Update, data: dict[str, Any]) -> str:
        nonlocal called
        called = True
        return "handled"

    result = await middleware(handler, update, {})

    assert result == "handled"
    assert called
    # Forwarding is fire-and-forget; give the task a turn to run.
    for _ in range(3):
        await _yield()
    assert repo.updates[0]["update_id"] == 1
    assert repo.updates[0]["message"]["text"] == "hello"


async def test_a_broken_update_payload_does_not_break_the_handler() -> None:
    repo = _RecordingRepository()
    middleware = _IncomingMiddleware(repo)  # type: ignore[arg-type]

    class _Unserializable(Update):
        def model_dump(self, **kwargs: Any) -> dict[str, Any]:
            raise ValueError("nope")

    async def handler(event: Update, data: dict[str, Any]) -> str:
        return "handled"

    result = await middleware(handler, _Unserializable(update_id=1), {})

    assert result == "handled"
    assert repo.updates == []


async def test_setup_is_idempotent() -> None:
    dp = Dispatcher()
    bot = Bot(token=BOT_TOKEN)
    before = len(dp.update.outer_middleware)
    middleware = _middleware()

    middleware.setup(dp, bot)
    middleware.setup(dp, bot)

    assert len(dp.update.outer_middleware) == before + 1
    # The dispatcher ships its own shutdown handlers (FSM); count only ours.
    ours = [h for h in dp.shutdown.handlers if h.callback == middleware.aclose]
    assert len(ours) == 1
    await middleware.aclose()


async def test_setup_registers_the_bot_and_patches_the_class_once() -> None:
    dp = Dispatcher()
    bot = Bot(token=BOT_TOKEN)
    middleware = _middleware()

    middleware.setup(dp, bot)
    patched = Bot.__call__

    SteeperMiddleware(base_url=BASE_URL, bot_id=BOT_ID, bot_token=BOT_TOKEN).setup(
        Dispatcher(), Bot(token="999:ZZZ")
    )

    assert Bot.__call__ is patched, "the class-level patch must be installed only once"
    assert bot in integration._bot_repos
    await middleware.aclose()


async def test_unregistered_bots_are_not_logged() -> None:
    """The patch is class-wide, so bots without Steeper must pass straight through."""
    dp = Dispatcher()
    bot = Bot(token=BOT_TOKEN)
    middleware = _middleware()
    middleware.setup(dp, bot)

    other = Bot(token="999:ZZZ")
    assert integration._bot_repos.get(other) is None
    await middleware.aclose()


@respx.mock
async def test_aclose_closes_the_http_client() -> None:
    middleware = _middleware()
    respx.post(middleware.repository.config.webhook_url).mock(return_value=httpx.Response(200))
    await middleware.repository.forward_update({"update_id": 1})

    await middleware.aclose()

    assert middleware.client._http.is_closed


async def test_dispatcher_shutdown_closes_the_client() -> None:
    dp = Dispatcher()
    bot = Bot(token=BOT_TOKEN)
    middleware = _middleware()
    middleware.setup(dp, bot)

    await dp.shutdown.trigger()

    assert middleware.client._http.is_closed


def test_repository_and_client_are_exposed() -> None:
    middleware = _middleware()

    assert isinstance(middleware.repository, SteeperRepository)
    assert middleware.client is middleware.repository.client


async def _yield() -> None:
    import asyncio

    await asyncio.sleep(0)
