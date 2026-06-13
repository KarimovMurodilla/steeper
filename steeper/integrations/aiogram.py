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
from collections.abc import Awaitable, Callable
from typing import Any
from weakref import WeakKeyDictionary

from steeper.repository import OutgoingMessageSnapshot, SteeperRepository, text_from_message_body

logger = logging.getLogger("steeper.aiogram")

try:
    from aiogram import BaseMiddleware, Bot, Dispatcher
    from aiogram.types import Message, Update
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


# Maps each registered Bot to its repository. A WeakKeyDictionary so wrapping a
# bot never keeps it alive. The class-level patch is installed once and consults
# this registry, so only bots set up with Steeper are logged.
_bot_repos: WeakKeyDictionary[Bot, SteeperRepository] = WeakKeyDictionary()
_orig_bot_call: Any = None


def _wrap_bot_api_call(bot: Bot, repository: SteeperRepository) -> None:
    """Intercept all Bot API calls; log any return value that is a Message (or list of them).

    aiogram dispatches every API method via ``await self(method)`` — an *implicit* call,
    which Python resolves through ``type(self).__call__`` rather than any instance attribute.
    So the wrapper must be installed on the class, not the instance; a per-bot registry keeps
    it scoped to bots that were actually set up with Steeper.
    """
    global _orig_bot_call
    _bot_repos[bot] = repository

    if _orig_bot_call is not None:
        return
    _orig_bot_call = Bot.__call__

    async def patched(
        self: Bot,
        method: Any,
        request_timeout: int | None = None,
    ) -> Any:
        result = await _orig_bot_call(self, method, request_timeout=request_timeout)
        repo = _bot_repos.get(self)
        if repo is not None:
            try:
                await _log_aiogram_outgoing(repo, result)
            except Exception:
                logger.debug("Failed to log outgoing message", exc_info=True)
        return result

    Bot.__call__ = patched  # type: ignore[method-assign]


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
