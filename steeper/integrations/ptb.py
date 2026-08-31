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

import hashlib
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from weakref import WeakSet

from steeper._background import fire_and_forget
from steeper._logging import LogCapture, LogCaptureOptions
from steeper.repository import OutgoingMessageSnapshot, SteeperRepository, text_from_message_body

logger = logging.getLogger("steeper.ptb")

try:
    from telegram import Bot, Message, Update
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


# Maps each registered bot to its repository, keyed by the SHA-256 of the bot
# token rather than by the Bot object: PTB's objects define ``__slots__`` and are
# not weak-referenceable, and the digest keeps the raw token out of this global.
_bot_repos: dict[str, SteeperRepository] = {}
_orig_bot_post: Any = None

# Applications already set up, so a repeated ``setup()`` can't stack a second
# handler (and a second shutdown callback) on one of them. A WeakSet rather than
# an attribute on the Application: under Python 3.13 its ``__slots__`` are
# enforced, so it has no ``__dict__`` to hold a marker.
_setup_applications: WeakSet[Application] = WeakSet()  # type: ignore[type-arg]


def _bot_key(bot: Any) -> str:
    return hashlib.sha256(bot.token.encode()).hexdigest()


def _wrap_bot_post(application: Application, repository: SteeperRepository) -> None:  # type: ignore[type-arg]
    """Intercept ``Bot._post`` so any response that decodes to Message(s) is logged.

    The wrapper is installed on :class:`telegram.Bot` itself rather than on the
    instance: PTB freezes its objects and defines ``__slots__``, so ``bot._post =
    ...`` raises ``AttributeError`` ("attribute '_post' is read-only"). A registry
    keyed by token digest keeps the patch scoped to bots actually set up with
    Steeper, and ``ExtBot`` inherits ``_post`` unchanged, so it is covered too.
    """
    global _orig_bot_post
    _bot_repos[_bot_key(application.bot)] = repository

    if _orig_bot_post is not None:
        return
    _orig_bot_post = Bot._post

    async def patched(
        self: Any,
        endpoint: str,
        data: Any = None,
        **kwargs: Any,
    ) -> Any:
        result = await _orig_bot_post(self, endpoint, data, **kwargs)
        repo = _bot_repos.get(_bot_key(self))
        if repo is not None:
            # Fire-and-forget so logging never delays the bot's own API call.
            fire_and_forget(_log_ptb_outgoing(self, repo, result))
        return result

    Bot._post = patched  # type: ignore[method-assign]


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
        capture_logs: bool = False,
        log_level: int | str = "INFO",
        log_batch_size: int = 100,
        log_flush_interval: float = 2.0,
        log_exclude_loggers: frozenset[str] | set[str] | None = None,
    ) -> None:
        """Create the integration.

        Args beyond the connection settings:
            capture_logs: Also ship the bot process's ``logging`` output to
                Steeper, so the platform can show its system logs.
            log_level: Minimum level captured. ``DEBUG`` on a chatty bot is a lot
                of traffic, hence the ``INFO`` default.
            log_batch_size: Records buffered before a batch is shipped.
            log_flush_interval: Seconds between flushes of a partial batch.
            log_exclude_loggers: Extra logger-name prefixes never shipped, on top
                of Steeper's own and its HTTP stack (which must stay excluded to
                avoid a logging loop).
        """
        self._repository = SteeperRepository(
            base_url=base_url,
            bot_id=bot_id,
            bot_token=bot_token,
            timeout=timeout,
        )
        self._log_capture = LogCapture(
            LogCaptureOptions(
                enabled=capture_logs,
                level=log_level,
                batch_size=log_batch_size,
                flush_interval=log_flush_interval,
                exclude_loggers=frozenset(log_exclude_loggers) if log_exclude_loggers else None,
            )
        )
        self._timeout = timeout

    def setup(self, application: Application) -> None:  # type: ignore[type-arg]
        """Register Steeper hooks on a PTB Application.

        - Incoming: a low-priority handler that captures every Update.
        - Outgoing: ``Bot._post`` is wrapped so JSON that represents sent/edited messages
          (``sendMessage``, ``sendPhoto``, ``sendMediaGroup``, ``editMessageText``, etc.) is
          logged to Steeper.
        """
        if application in _setup_applications:
            logger.debug("Steeper is already set up on this application; ignoring")
            return
        _setup_applications.add(application)

        application.add_handler(_SteeperHandler(self._repository), group=-1)
        _wrap_bot_post(application, self._repository)
        _chain_post_shutdown(application, self.aclose)
        self._log_capture.start(self._repository.config, timeout=self._timeout)
        logger.info("Steeper middleware registered for python-telegram-bot")

    async def aclose(self) -> None:
        """Close the underlying HTTP client.

        Chained onto ``Application.post_shutdown`` by :meth:`setup`, so bots driven by
        ``run_polling``/``run_webhook`` need not call it. A bare ``Application.shutdown()``
        does *not* run ``post_shutdown``, so call this yourself if you manage the
        application lifecycle by hand.
        """
        await self._log_capture.astop()
        await self._repository.aclose()

    @property
    def repository(self) -> SteeperRepository:
        return self._repository

    @property
    def client(self):
        """Compatibility alias for :attr:`repository.client`."""
        return self._repository.client
