"""Steeper middleware for **aiogram v3**.

Usage::

    from aiogram import Bot, Dispatcher
    from steeper.integrations.aiogram import SteeperMiddleware

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    steeper = SteeperMiddleware(
        base_url="http://localhost:8000",
        bot_id="<uuid>",
        bot_token=BOT_TOKEN,
    )
    steeper.setup(dp, bot)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

from steeper._client import SteeperClient
from steeper._config import SteeperConfig

logger = logging.getLogger("steeper.aiogram")

try:
    from aiogram import BaseMiddleware, Bot, Dispatcher
    from aiogram.types import Update, Message
except ImportError as _exc:
    raise ImportError(
        "aiogram>=3.0 is required for this integration. "
        "Install it with: pip install steeper[aiogram]"
    ) from _exc


class _IncomingMiddleware(BaseMiddleware):
    """Outer middleware on ``Update`` — forwards raw updates to Steeper."""

    def __init__(self, client: SteeperClient) -> None:
        self._client = client

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        raw = event.model_dump(mode="json")
        await self._client.forward_update(raw)
        return await handler(event, data)


class _OutgoingMiddleware(BaseMiddleware):
    """Outer middleware on ``Message`` (response) — catches bot replies."""

    def __init__(self, client: SteeperClient) -> None:
        self._client = client

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)
        if isinstance(result, Message):
            await self._client.log_bot_message(
                chat_id=result.chat.id,
                text=result.text or result.caption or "",
                message_id=result.message_id,
                date=int(result.date.timestamp()) if result.date else None,
            )
        return result


def _wrap_bot_send(bot: Bot, client: SteeperClient) -> None:
    """Monkey-patch ``Bot.send_message`` to also log to Steeper."""
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
    """All-in-one Steeper integration for aiogram v3.

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

    def setup(self, dp: Dispatcher, bot: Bot) -> None:
        """Register Steeper on the dispatcher and bot.

        - Incoming updates are forwarded via an outer Update middleware.
        - Outgoing ``send_message`` calls are patched to log bot replies.
        """
        dp.update.outer_middleware(self._incoming)
        _wrap_bot_send(bot, self._client)
        logger.info("Steeper middleware registered for aiogram")

    @property
    def _incoming(self) -> _IncomingMiddleware:
        return _IncomingMiddleware(self._client)

    @property
    def client(self) -> SteeperClient:
        return self._client
