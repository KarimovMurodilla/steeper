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

from steeper._client import SteeperClient
from steeper._config import SteeperConfig

logger = logging.getLogger("steeper.telebot")

try:
    import telebot as _telebot
    from telebot import types as tg_types
except ImportError as _exc:
    raise ImportError(
        "pyTelegramBotAPI>=4.0 is required for this integration. "
        "Install it with: pip install steeper[telebot]"
    ) from _exc


def _run_async(coro: Any) -> None:
    """Fire-and-forget an async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


def _update_to_dict(update: tg_types.Update) -> dict[str, Any]:
    """Convert a telebot Update to a Telegram-compatible dict."""
    raw: dict[str, Any] = {"update_id": update.update_id}

    if update.message:
        raw["message"] = _message_to_dict(update.message)
    if update.edited_message:
        raw["edited_message"] = _message_to_dict(update.edited_message)
    return raw


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
        self._config = SteeperConfig(
            base_url=base_url,
            bot_id=bot_id,
            bot_token=bot_token,
        )
        self._client = SteeperClient(self._config, timeout=timeout)

    def setup(self, bot: _telebot.TeleBot) -> None:
        """Register Steeper hooks on a sync TeleBot instance.

        - Incoming: ``middleware_handler`` that fires on every update.
        - Outgoing: ``send_message`` is patched to log bot replies.
        """
        bot.use_class_middlewares = True

        class _Incoming(_telebot.handler_backends.BaseMiddleware):
            update_types = ["message", "edited_message"]

            def __init__(self_inner) -> None:  # noqa: N805
                super().__init__()
                self_inner.client = self._client

            def pre_process(self_inner, message: tg_types.Message, data: dict[str, Any]) -> None:  # noqa: N805
                update_dict: dict[str, Any] = {
                    "update_id": 0,
                    "message": _message_to_dict(message),
                }
                _run_async(self_inner.client.forward_update(update_dict))

            def post_process(self_inner, message: tg_types.Message, data: dict[str, Any], exception: BaseException | None) -> None:  # noqa: N805
                pass

        bot.register_middleware_handler(_Incoming())

        _original_send = bot.send_message

        def _patched_send(*args: Any, **kwargs: Any) -> tg_types.Message:
            result: tg_types.Message = _original_send(*args, **kwargs)
            try:
                _run_async(
                    self._client.log_bot_message(
                        chat_id=result.chat.id,
                        text=result.text or result.caption or "",
                        message_id=result.message_id,
                        date=result.date or int(time.time()),
                    )
                )
            except Exception:
                logger.debug("Failed to log outgoing message", exc_info=True)
            return result

        bot.send_message = _patched_send  # type: ignore[assignment]

        logger.info("Steeper middleware registered for pyTelegramBotAPI")

    @property
    def client(self) -> SteeperClient:
        return self._client
