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
import types
from typing import Any

from steeper.repository import OutgoingMessageSnapshot, SteeperRepository, text_from_message_body

logger = logging.getLogger("steeper.ptb")

try:
    from telegram import Message, Update
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


def _user_to_dict(user: Any) -> dict[str, Any]:
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


def _chat_to_dict(chat: Any) -> dict[str, Any]:
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


class _SteeperHandler(BaseHandler[Update, ContextTypes.DEFAULT_TYPE, None]):
    """Low-priority handler that intercepts every update for Steeper logging."""

    def __init__(self, repository: SteeperRepository) -> None:
        super().__init__(callback=self._noop)
        self._repository = repository

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
        await self._repository.forward_update(raw)

    @staticmethod
    async def _noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass


def _messages_from_ptb_post_result(bot: Any, result: Any) -> list[Message]:
    """Turn raw ``_post`` JSON into :class:`telegram.Message` instances when applicable."""
    if result is True:
        return []
    if isinstance(result, dict) and "message_id" in result:
        m = Message.de_json(result, bot)
        return [m] if m else []
    if isinstance(result, list) and result:
        if isinstance(result[0], dict) and "message_id" in result[0]:
            return Message.de_list(result, bot)
    return []


def _snapshot_from_ptb_message(message: Message) -> OutgoingMessageSnapshot:
    text = text_from_message_body(text=message.text, caption=message.caption)
    date_val = int(message.date.timestamp()) if message.date else None
    return OutgoingMessageSnapshot(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        date=date_val,
    )


def _wrap_bot_post(application: Application, repository: SteeperRepository) -> None:  # type: ignore[type-arg]
    """Wrap ``Bot._post`` so any response that decodes to Message(s) is logged."""
    bot = application.bot
    orig = bot._post

    async def patched(
        self: Any,
        endpoint: str,
        data: Any = None,
        **kwargs: Any,
    ) -> Any:
        result = await orig(endpoint, data, **kwargs)
        try:
            for msg in _messages_from_ptb_post_result(bot, result):
                await repository.record_outgoing(_snapshot_from_ptb_message(msg))
        except Exception:
            logger.debug("Failed to log outgoing message", exc_info=True)
        return result

    bot._post = types.MethodType(patched, bot)  # type: ignore[assignment]


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
        self._repository = SteeperRepository(
            base_url=base_url,
            bot_id=bot_id,
            bot_token=bot_token,
            timeout=timeout,
        )

    def setup(self, application: Application) -> None:  # type: ignore[type-arg]
        """Register Steeper hooks on a PTB Application.

        - Incoming: a low-priority handler that captures every Update.
        - Outgoing: ``Bot._post`` is wrapped so JSON that represents sent/edited messages
          (``sendMessage``, ``sendPhoto``, ``sendMediaGroup``, ``editMessageText``, etc.) is
          logged to Steeper.
        """
        application.add_handler(_SteeperHandler(self._repository), group=-1)
        _wrap_bot_post(application, self._repository)
        logger.info("Steeper middleware registered for python-telegram-bot")

    @property
    def repository(self) -> SteeperRepository:
        return self._repository

    @property
    def client(self):
        """Compatibility alias for :attr:`repository.client`."""
        return self._repository.client

