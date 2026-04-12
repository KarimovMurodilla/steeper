"""Steeper middleware for **python-telegram-bot** (PTB v20+).

Usage::

    from telegram.ext import ApplicationBuilder
    from steeper.integrations.ptb import SteeperMiddleware

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    steeper = SteeperMiddleware(
        base_url="http://localhost:8000",
        bot_id="<uuid>",
        bot_token=BOT_TOKEN,
    )
    steeper.setup(app)
"""

from __future__ import annotations

import logging
import time
from typing import Any

from steeper._client import SteeperClient
from steeper._config import SteeperConfig

logger = logging.getLogger("steeper.ptb")

try:
    from telegram import Message, Update, User, Chat
    from telegram.ext import (
        Application,
        BaseHandler,
        ContextTypes,
    )
except ImportError as _exc:
    raise ImportError(
        "python-telegram-bot>=20.0 is required for this integration. "
        "Install it with: pip install steeper[ptb]"
    ) from _exc


def _update_to_dict(update: Update) -> dict[str, Any]:
    """Convert a PTB Update to a Telegram-compatible dict."""
    raw: dict[str, Any] = {"update_id": update.update_id}

    if update.message:
        raw["message"] = _message_to_dict(update.message)
    if update.edited_message:
        raw["edited_message"] = _message_to_dict(update.edited_message)
    return raw


def _user_to_dict(user: User) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": user.id,
        "is_bot": user.is_bot,
        "first_name": user.first_name,
    }
    if user.last_name:
        data["last_name"] = user.last_name
    if user.username:
        data["username"] = user.username
    if user.language_code:
        data["language_code"] = user.language_code
    return data


def _chat_to_dict(chat: Chat) -> dict[str, Any]:
    data: dict[str, Any] = {"id": chat.id, "type": chat.type}
    if chat.title:
        data["title"] = chat.title
    if chat.username:
        data["username"] = chat.username
    if chat.first_name:
        data["first_name"] = chat.first_name
    if chat.last_name:
        data["last_name"] = chat.last_name
    return data


def _message_to_dict(msg: Message) -> dict[str, Any]:
    data: dict[str, Any] = {
        "message_id": msg.message_id,
        "chat": _chat_to_dict(msg.chat),
        "date": int(msg.date.timestamp()) if msg.date else int(time.time()),
    }
    if msg.from_user:
        data["from"] = _user_to_dict(msg.from_user)
    if msg.text:
        data["text"] = msg.text
    if msg.caption:
        data["caption"] = msg.caption
    return data


class _SteeperHandler(BaseHandler[Update, ContextTypes.DEFAULT_TYPE]):
    """Low-priority handler that intercepts every update for Steeper logging."""

    def __init__(self, client: SteeperClient) -> None:
        super().__init__(callback=self._noop)
        self._client = client

    def check_update(self, update: object) -> bool:
        return isinstance(update, Update)

    async def handle_update(
        self,
        update: Update,
        application: Application,  # type: ignore[type-arg]
        check_result: Any,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        raw = _update_to_dict(update)
        await self._client.forward_update(raw)

    @staticmethod
    async def _noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass


def _wrap_bot_send(application: Application, client: SteeperClient) -> None:  # type: ignore[type-arg]
    """Patch ``Bot.send_message`` to also log to Steeper."""
    bot = application.bot
    _original_send = bot.send_message

    async def _patched_send(*args: Any, **kwargs: Any) -> Message:
        result: Message = await _original_send(*args, **kwargs)
        try:
            await client.log_bot_message(
                chat_id=result.chat.id,
                text=result.text or result.caption or "",
                message_id=result.message_id,
                date=int(result.date.timestamp()) if result.date else None,
            )
        except Exception:
            logger.debug("Failed to log outgoing message", exc_info=True)
        return result

    bot.send_message = _patched_send  # type: ignore[assignment]


class SteeperMiddleware:
    """All-in-one Steeper integration for python-telegram-bot v20+.

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

    def setup(self, application: Application) -> None:  # type: ignore[type-arg]
        """Register Steeper hooks on a PTB Application.

        - Incoming: a low-priority handler that captures every Update.
        - Outgoing: ``Bot.send_message`` is patched to log bot replies.
        """
        application.add_handler(_SteeperHandler(self._client), group=-1)
        _wrap_bot_send(application, self._client)
        logger.info("Steeper middleware registered for python-telegram-bot")

    @property
    def client(self) -> SteeperClient:
        return self._client
