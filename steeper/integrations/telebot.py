"""Steeper middleware for **pyTelegramBotAPI** (telebot).

Usage::

    import telebot
    from steeper.integrations.telebot import SteeperMiddleware

    bot = telebot.TeleBot(BOT_TOKEN)

    steeper = SteeperMiddleware(
        base_url="http://localhost:8000",
        bot_id="<uuid>",
        bot_token=BOT_TOKEN,
    )
    steeper.setup(bot)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from steeper.repository import OutgoingMessageSnapshot, SteeperRepository, text_from_message_body

logger = logging.getLogger("steeper.telebot")

try:
    import telebot as _telebot
    from telebot import apihelper as _apihelper
    from telebot import types as tg_types
except ImportError as _exc:
    raise ImportError(
        "pyTelegramBotAPI>=4.0 is required for this integration. "
        "Install it with: pip install steeper[telebot]"
    ) from _exc

_apihelper_orig: Any = None
_token_repos: dict[str, SteeperRepository] = {}


def _run_async(coro: Any) -> None:
    """Fire-and-forget an async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


def _telebot_snapshots_from_result(result: Any) -> list[OutgoingMessageSnapshot]:
    """Build snapshots from raw ``apihelper`` JSON (``result`` field)."""
    if result is None or result is True:
        return []
    if isinstance(result, dict) and "message_id" in result and "chat" in result:
        return [_snapshot_from_telebot_dict(result)]
    if isinstance(result, list):
        out: list[OutgoingMessageSnapshot] = []
        for item in result:
            if isinstance(item, dict) and "message_id" in item and "chat" in item:
                out.append(_snapshot_from_telebot_dict(item))
        return out
    return []


def _snapshot_from_telebot_dict(d: dict[str, Any]) -> OutgoingMessageSnapshot:
    chat = d["chat"]
    chat_id = chat["id"] if isinstance(chat, dict) else chat.id
    text = text_from_message_body(text=d.get("text"), caption=d.get("caption"))
    raw_date = d.get("date")
    date_val: int | None
    if isinstance(raw_date, int):
        date_val = raw_date
    elif isinstance(raw_date, float):
        date_val = int(raw_date)
    else:
        date_val = None
    return OutgoingMessageSnapshot(
        chat_id=chat_id,
        message_id=d["message_id"],
        text=text,
        date=date_val,
    )


def _ensure_apihelper_patch() -> None:
    global _apihelper_orig
    if _apihelper_orig is not None:
        return

    _apihelper_orig = _apihelper._make_request

    def _wrapped(
        token: str,
        method_name: str,
        method: str = "get",
        params: Any = None,
        files: Any = None,
    ) -> Any:
        assert _apihelper_orig is not None
        result = _apihelper_orig(token, method_name, method, params, files)
        repo = _token_repos.get(token)
        if repo is None:
            return result
        for snap in _telebot_snapshots_from_result(result):
            _run_async(repo.record_outgoing(snap))
        return result

    _apihelper._make_request = _wrapped  # type: ignore[assignment]


class SteeperMiddleware:
    """All-in-one Steeper integration for pyTelegramBotAPI.

    Call :meth:`setup` to register both incoming and outgoing hooks.
    """

    def __init__(
        self,
        base_url: str,
        bot_id: str,
        bot_token: str,
        *,
        timeout: float = 10.0,
    ) -> None:
        self._repository = SteeperRepository(
            base_url=base_url,
            bot_id=bot_id,
            bot_token=bot_token,
            timeout=timeout,
        )

    def setup(self, bot: _telebot.TeleBot) -> None:
        """Register Steeper hooks on a sync TeleBot instance.

        - Incoming: ``middleware_handler`` that fires on every update.
        - Outgoing: ``telebot.apihelper._make_request`` is wrapped (scoped to this bot's token)
          so API responses that contain full message objects are logged to Steeper.
        """
        _token_repos[bot.token] = self._repository
        _ensure_apihelper_patch()

        bot.use_class_middlewares = True

        class _Incoming(_telebot.handler_backends.BaseMiddleware):
            update_types = ["message", "edited_message"]

            def __init__(self_inner) -> None:  # noqa: N805
                super().__init__()
                self_inner.repository = self._repository

            def pre_process(self_inner, message: tg_types.Message, data: dict[str, Any]) -> None:  # noqa: N805
                update_dict: dict[str, Any] = {
                    "update_id": 0,
                    "message": _message_to_dict(message),
                }
                _run_async(self_inner.repository.forward_update(update_dict))

            def post_process(self_inner, message: tg_types.Message, data: dict[str, Any], exception: BaseException | None) -> None:  # noqa: N805
                pass

        bot.register_middleware_handler(_Incoming())

        logger.info("Steeper middleware registered for pyTelegramBotAPI")

    @property
    def repository(self) -> SteeperRepository:
        return self._repository

    @property
    def client(self):
        """Compatibility alias for :attr:`repository.client`."""
        return self._repository.client


def _message_to_dict(msg: tg_types.Message) -> dict[str, Any]:
    """Convert a telebot Message to a Telegram-compatible dict."""
    data: dict[str, Any] = {
        "message_id": msg.message_id,
        "chat": {"id": msg.chat.id, "type": msg.chat.type},
        "date": msg.date or int(time.time()),
    }
    if msg.chat.title:
        data["chat"]["title"] = msg.chat.title
    if msg.chat.username:
        data["chat"]["username"] = msg.chat.username
    if msg.chat.first_name:
        data["chat"]["first_name"] = msg.chat.first_name
    if msg.chat.last_name:
        data["chat"]["last_name"] = msg.chat.last_name

    if msg.from_user:
        data["from"] = {
            "id": msg.from_user.id,
            "is_bot": msg.from_user.is_bot,
            "first_name": msg.from_user.first_name,
        }
        if msg.from_user.last_name:
            data["from"]["last_name"] = msg.from_user.last_name
        if msg.from_user.username:
            data["from"]["username"] = msg.from_user.username
        if msg.from_user.language_code:
            data["from"]["language_code"] = msg.from_user.language_code

    if msg.text:
        data["text"] = msg.text
    if msg.caption:
        data["caption"] = msg.caption
    return data
