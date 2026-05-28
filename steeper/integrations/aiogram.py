"""Steeper middleware for **aiogram v3**.

Usage (async entrypoint + :meth:`Dispatcher.start_polling`)::

    import asyncio
    from aiogram import Bot, Dispatcher
    from steeper.integrations.aiogram import SteeperMiddleware

    async def main() -> None:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()
        SteeperMiddleware(...).setup(dp, bot)
        await dp.start_polling(bot)

    asyncio.run(main())
"""

from __future__ import annotations

import logging
import types
from typing import Any, Callable, Awaitable

from steeper.repository import OutgoingMessageSnapshot, SteeperRepository, text_from_message_body

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

    def __init__(self, repository: SteeperRepository) -> None:
        self._repository = repository

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        raw = event.model_dump(mode="json")
        await self._repository.forward_update(raw)
        return await handler(event, data)


def _snapshot_from_aiogram_message(message: Message) -> OutgoingMessageSnapshot:
    text = text_from_message_body(text=message.text, caption=message.caption)
    date_val = int(message.date.timestamp()) if message.date else None
    return OutgoingMessageSnapshot(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        date=date_val,
    )


async def _log_aiogram_outgoing(repository: SteeperRepository, result: Any) -> None:
    if isinstance(result, Message):
        await repository.record_outgoing(_snapshot_from_aiogram_message(result))
        return
    if isinstance(result, list) and result and isinstance(result[0], Message):
        for msg in result:
            await repository.record_outgoing(_snapshot_from_aiogram_message(msg))


def _wrap_bot_api_call(bot: Bot, repository: SteeperRepository) -> None:
    """Intercept all Bot API calls; log any return value that is a Message (or list of them)."""
    orig = type(bot).__call__

    async def patched(
        self: Bot,
        method: Any,
        request_timeout: int | None = None,
    ) -> Any:
        result = await orig(self, method, request_timeout=request_timeout)
        try:
            await _log_aiogram_outgoing(repository, result)
        except Exception:
            logger.debug("Failed to log outgoing message", exc_info=True)
        return result

    bot.__call__ = types.MethodType(patched, bot)  # type: ignore[method-assign]


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
        self._repository = SteeperRepository(
            base_url=base_url,
            bot_id=bot_id,
            bot_token=bot_token,
            timeout=timeout,
        )

    def setup(self, dp: Dispatcher, bot: Bot) -> None:
        """Register Steeper on the dispatcher and bot.

        - Incoming updates are forwarded via an outer Update middleware.
        - Outgoing traffic is observed by wrapping :meth:`Bot.__call__`, so any API call that
          returns a :class:`~aiogram.types.Message` (``send_message``, ``send_photo``, media
          groups, etc.) is logged to Steeper.
        """
        dp.update.outer_middleware(self._incoming)
        _wrap_bot_api_call(bot, self._repository)
        logger.info("Steeper middleware registered for aiogram")

    @property
    def _incoming(self) -> _IncomingMiddleware:
        return _IncomingMiddleware(self._repository)

    @property
    def repository(self) -> SteeperRepository:
        return self._repository

    @property
    def client(self):
        """Compatibility alias for :attr:`repository.client`."""
        return self._repository.client

