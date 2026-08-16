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
import types
from collections.abc import Awaitable, Callable
from typing import Any

from steeper._background import fire_and_forget
from steeper.repository import OutgoingMessageSnapshot, SteeperRepository, text_from_message_body

logger = logging.getLogger("steeper.ptb")

# Marks a bot whose ``_post`` is already wrapped, so a repeated ``setup()`` can't
# nest a second wrapper and log every outgoing message twice.
_SETUP_MARKER = "_steeper_setup"

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
        # Fire-and-forget: PTB processes updates sequentially by default, so
        # awaiting the Steeper round-trip here would stall the whole bot
        # whenever the backend is slow or unreachable.
        try:
            raw = update.to_dict(recursive=True)
        except Exception:
            logger.debug("Failed to build update payload", exc_info=True)
            return
        fire_and_forget(self._repository.forward_update(raw))

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
            return list(Message.de_list(result, bot))
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


async def _log_ptb_outgoing(bot: Any, repository: SteeperRepository, result: Any) -> None:
    for msg in _messages_from_ptb_post_result(bot, result):
        await repository.record_outgoing(_snapshot_from_ptb_message(msg))


def _wrap_bot_post(application: Application, repository: SteeperRepository) -> None:  # type: ignore[type-arg]
    """Wrap ``Bot._post`` so any response that decodes to Message(s) is logged."""
    bot = application.bot
    if getattr(bot, _SETUP_MARKER, False):
        return
    setattr(bot, _SETUP_MARKER, True)

    orig = bot._post

    async def patched(
        self: Any,
        endpoint: str,
        data: Any = None,
        **kwargs: Any,
    ) -> Any:
        result = await orig(endpoint, data, **kwargs)
        # Fire-and-forget so logging never delays the bot's own API call.
        fire_and_forget(_log_ptb_outgoing(bot, repository, result))
        return result

    bot._post = types.MethodType(patched, bot)  # type: ignore[assignment]


def _chain_post_shutdown(
    application: Application,  # type: ignore[type-arg]
    close: Callable[[], Awaitable[None]],
) -> None:
    """Append ``close`` to the application's ``post_shutdown`` callback.

    ``post_shutdown`` holds at most one callback, and the host application may already
    have set its own, so chain rather than overwrite. PTB awaits it from
    ``run_polling``/``run_webhook`` only.
    """
    orig = getattr(application, "post_shutdown", None)

    async def patched(app: Application) -> None:  # type: ignore[type-arg]
        try:
            if orig is not None:
                await orig(app)
        finally:
            await close()

    application.post_shutdown = patched


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
        if getattr(application, _SETUP_MARKER, False):
            logger.debug("Steeper is already set up on this application; ignoring")
            return
        setattr(application, _SETUP_MARKER, True)

        application.add_handler(_SteeperHandler(self._repository), group=-1)
        _wrap_bot_post(application, self._repository)
        _chain_post_shutdown(application, self.aclose)
        logger.info("Steeper middleware registered for python-telegram-bot")

    async def aclose(self) -> None:
        """Close the underlying HTTP client.

        Chained onto ``Application.post_shutdown`` by :meth:`setup`, so bots driven by
        ``run_polling``/``run_webhook`` need not call it. A bare ``Application.shutdown()``
        does *not* run ``post_shutdown``, so call this yourself if you manage the
        application lifecycle by hand.
        """
        await self._repository.aclose()

    @property
    def repository(self) -> SteeperRepository:
        return self._repository

    @property
    def client(self):
        """Compatibility alias for :attr:`repository.client`."""
        return self._repository.client
