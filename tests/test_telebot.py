"""Tests for the pyTelegramBotAPI integration.

The integration patches ``apihelper._make_request`` process-wide and keys its
registry by bot token, so every test restores both.
"""

import json
import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import respx
import telebot
from telebot import apihelper

from steeper import _background
from steeper.integrations import telebot as integration
from steeper.integrations.telebot import (
    SteeperMiddleware,
    _full_update_from_telebot,
    _snapshot_from_telebot_dict,
    _telebot_snapshots_from_result,
)
from steeper.repository import OutgoingMessageSnapshot, SteeperRepository

BOT_ID = "d74d82b4-7c00-408d-b611-2411e0b3c6f8"
BOT_TOKEN = "123456:ABC-DEF"
BASE_URL = "https://api.example.com"

_MESSAGE = {
    "message_id": 7,
    "chat": {"id": 42, "type": "private"},
    "date": 1700000000,
    "text": "hello",
}


@pytest.fixture(autouse=True)
def _restore_patch_state() -> Iterator[None]:
    orig_request = apihelper._make_request
    saved = integration._apihelper_orig
    yield
    apihelper._make_request = orig_request
    integration._apihelper_orig = saved
    integration._token_repos.clear()


def _middleware() -> SteeperMiddleware:
    return SteeperMiddleware(base_url=BASE_URL, bot_id=BOT_ID, bot_token=BOT_TOKEN)


def _drain_background(timeout: float = 5.0) -> None:
    """Wait for fire-and-forget work to finish, so assertions aren't racing it."""
    deadline = time.monotonic() + timeout
    while _background._background_loop._in_flight and time.monotonic() < deadline:
        time.sleep(0.01)


def test_snapshot_from_a_message_dict() -> None:
    assert _snapshot_from_telebot_dict(_MESSAGE) == OutgoingMessageSnapshot(
        chat_id=42, message_id=7, text="hello", date=1700000000
    )


def test_snapshot_falls_back_to_caption() -> None:
    payload = {**_MESSAGE, "text": None, "caption": "  a photo  "}

    assert _snapshot_from_telebot_dict(payload).text == "a photo"


def test_snapshot_coerces_a_float_date() -> None:
    assert _snapshot_from_telebot_dict({**_MESSAGE, "date": 1700000000.9}).date == 1700000000


def test_snapshot_tolerates_a_missing_date() -> None:
    payload = {k: v for k, v in _MESSAGE.items() if k != "date"}

    assert _snapshot_from_telebot_dict(payload).date is None


def test_snapshots_from_a_single_message_result() -> None:
    assert [s.message_id for s in _telebot_snapshots_from_result(_MESSAGE)] == [7]


def test_snapshots_from_a_media_group_result() -> None:
    group = [_MESSAGE, {**_MESSAGE, "message_id": 8}]

    assert [s.message_id for s in _telebot_snapshots_from_result(group)] == [7, 8]


@pytest.mark.parametrize(
    "result",
    [None, True, {"ok": True}, [{"not": "a message"}], "text", 42],
)
def test_results_that_are_not_messages_yield_no_snapshots(result: Any) -> None:
    assert _telebot_snapshots_from_result(result) == []


def test_full_update_keeps_update_id_and_sub_objects() -> None:
    raw = json.dumps({"update_id": 99, "message": _MESSAGE})
    update = telebot.types.Update.de_json(raw)

    rebuilt = _full_update_from_telebot(update)

    assert rebuilt["update_id"] == 99
    assert rebuilt["message"]["message_id"] == 7
    assert rebuilt["message"]["chat"]["id"] == 42


def test_full_update_carries_non_message_update_types() -> None:
    raw = json.dumps(
        {
            "update_id": 100,
            "callback_query": {
                "id": "cb1",
                "from": {"id": 42, "is_bot": False, "first_name": "A"},
                "chat_instance": "ci",
                "data": "press",
            },
        }
    )
    update = telebot.types.Update.de_json(raw)

    rebuilt = _full_update_from_telebot(update)

    assert rebuilt["update_id"] == 100
    assert rebuilt["callback_query"]["data"] == "press"


def test_full_update_skips_a_sub_object_with_unparsable_json() -> None:
    raw = json.dumps({"update_id": 101, "message": _MESSAGE})
    update = telebot.types.Update.de_json(raw)
    update.message.json = "{not json"

    rebuilt = _full_update_from_telebot(update)

    assert rebuilt == {"update_id": 101}


@respx.mock
def test_incoming_updates_are_forwarded() -> None:
    middleware = _middleware()
    route = respx.post(middleware.repository.config.webhook_url).mock(
        return_value=httpx.Response(200)
    )
    bot = telebot.TeleBot(BOT_TOKEN)
    middleware.setup(bot)
    update = telebot.types.Update.de_json(json.dumps({"update_id": 5, "message": _MESSAGE}))

    bot.process_new_updates([update])
    _drain_background()

    assert route.called
    assert json.loads(route.calls.last.request.content)["update_id"] == 5
    middleware.close()


@respx.mock
def test_outgoing_messages_are_logged_for_the_registered_token() -> None:
    middleware = _middleware()
    route = respx.post(middleware.repository.config.bot_message_url).mock(
        return_value=httpx.Response(200)
    )
    bot = telebot.TeleBot(BOT_TOKEN)
    apihelper._make_request = lambda *args, **kwargs: _MESSAGE  # type: ignore[assignment]
    middleware.setup(bot)

    apihelper._make_request(BOT_TOKEN, "sendMessage", "post", {})
    _drain_background()

    assert route.called
    payload = json.loads(route.calls.last.request.content)
    assert payload == {"chat_id": 42, "text": "hello", "message_id": 7, "date": 1700000000}
    middleware.close()


@respx.mock
def test_other_bots_sharing_the_process_are_not_logged() -> None:
    """The apihelper patch is global, so it must be scoped by token."""
    middleware = _middleware()
    route = respx.post(middleware.repository.config.bot_message_url).mock(
        return_value=httpx.Response(200)
    )
    bot = telebot.TeleBot(BOT_TOKEN)
    apihelper._make_request = lambda *args, **kwargs: _MESSAGE  # type: ignore[assignment]
    middleware.setup(bot)

    apihelper._make_request("999:UNREGISTERED", "sendMessage", "post", {})
    _drain_background()

    assert not route.called
    middleware.close()


def test_a_failing_forward_does_not_break_the_api_call() -> None:
    middleware = _middleware()
    bot = telebot.TeleBot(BOT_TOKEN)
    apihelper._make_request = lambda *args, **kwargs: _MESSAGE  # type: ignore[assignment]
    middleware.setup(bot)

    # No respx mock here: the backend call fails, and the bot must not notice.
    assert apihelper._make_request(BOT_TOKEN, "sendMessage", "post", {}) == _MESSAGE
    _drain_background()
    middleware.close()


@respx.mock
def test_setup_is_idempotent() -> None:
    middleware = _middleware()
    route = respx.post(middleware.repository.config.webhook_url).mock(
        return_value=httpx.Response(200)
    )
    bot = telebot.TeleBot(BOT_TOKEN)

    middleware.setup(bot)
    middleware.setup(bot)

    update = telebot.types.Update.de_json(json.dumps({"update_id": 5, "message": _MESSAGE}))
    bot.process_new_updates([update])
    _drain_background()

    assert len(route.calls) == 1, "a second setup() must not double-forward"
    middleware.close()


def test_apihelper_is_patched_only_once() -> None:
    bot = telebot.TeleBot(BOT_TOKEN)
    first = _middleware()
    first.setup(bot)
    patched = apihelper._make_request

    second = SteeperMiddleware(base_url=BASE_URL, bot_id=BOT_ID, bot_token="999:ZZZ")
    second.setup(telebot.TeleBot("999:ZZZ"))

    assert apihelper._make_request is patched
    first.close()
    second.close()


def test_close_closes_the_http_client() -> None:
    middleware = _middleware()

    middleware.close()

    assert middleware.client._http.is_closed


def test_close_is_safe_to_call_twice() -> None:
    middleware = _middleware()

    middleware.close()
    middleware.close()

    assert middleware.client._http.is_closed


def test_repository_and_client_are_exposed() -> None:
    middleware = _middleware()

    assert isinstance(middleware.repository, SteeperRepository)
    assert middleware.client is middleware.repository.client
    middleware.close()
