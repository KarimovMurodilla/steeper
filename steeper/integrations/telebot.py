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

import json
import logging
from typing import Any

from steeper._background import fire_and_forget_threadsafe, run_threadsafe
from steeper._events import EventTracker
from steeper._logging import LogCapture, LogCaptureOptions
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

# Marks a bot whose ``process_new_updates`` is already wrapped, so a repeated
# ``setup()`` can't nest a second wrapper and forward every update twice.
_SETUP_MARKER = "_steeper_setup"


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
        try:
            repo = _token_repos.get(token)
            if repo is not None:
                for snap in _telebot_snapshots_from_result(result):
                    fire_and_forget_threadsafe(repo.record_outgoing(snap))
        except Exception:
            # Logging to Steeper must never break the bot's own API call.
            logger.debug("Failed to log outgoing telebot message", exc_info=True)
        return result

    _apihelper._make_request = _wrapped  # type: ignore[assignment]


# Attributes on a telebot ``Update`` that are not themselves update payloads.
_UPDATE_META_FIELDS = frozenset({"update_id", "json"})


def _full_update_from_telebot(update: tg_types.Update) -> dict[str, Any]:
    """Reconstruct a full, Telegram-shaped update dict from a telebot ``Update``.

    telebot doesn't keep the raw update JSON, but it preserves ``update_id`` and the
    raw ``.json`` of every parsed sub-object (``message``, ``callback_query``,
    ``inline_query``, ``channel_post``, …). We forward whichever ones are present so
    the backend receives the same full fidelity as the aiogram integration.
    """
    raw: dict[str, Any] = {"update_id": update.update_id}
    for name, value in vars(update).items():
        if name in _UPDATE_META_FIELDS or value is None:
            continue
        sub = getattr(value, "json", None)
        if isinstance(sub, str):
            try:
                sub = json.loads(sub)
            except ValueError:
                continue
        if isinstance(sub, dict):
            raw[name] = sub
    return raw


def _wrap_process_new_updates(bot: _telebot.TeleBot, repository: SteeperRepository) -> None:
    """Wrap ``TeleBot.process_new_updates`` — the single funnel for every update type.

    This covers both polling and webhook dispatch and yields the real ``update_id``,
    unlike a message-only middleware.
    """
    if getattr(bot, _SETUP_MARKER, False):
        return
    setattr(bot, _SETUP_MARKER, True)

    orig = bot.process_new_updates

    def patched(updates: Any) -> Any:
        for update in updates or []:
            try:
                raw = _full_update_from_telebot(update)
            except Exception:
                logger.debug("Failed to build update payload", exc_info=True)
                continue
            fire_and_forget_threadsafe(repository.forward_update(raw))
        return orig(updates)

    bot.process_new_updates = patched  # type: ignore[assignment]


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
        event_batch_size: int = 50,
        event_flush_interval: float = 5.0,
        capture_logs: bool = False,
        log_level: int | str = "INFO",
        log_batch_size: int = 100,
        log_flush_interval: float = 2.0,
        log_exclude_loggers: frozenset[str] | set[str] | None = None,
    ) -> None:
        """Create the integration.

        Args beyond the connection settings:
            event_batch_size: Events buffered by :meth:`track` before a batch is
                shipped early.
            event_flush_interval: Seconds between flushes of a partial event
                batch. Events are far rarer than log records, so this is longer
                than its logging counterpart.
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
            event_batch_size=event_batch_size,
            event_flush_interval=event_flush_interval,
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

    def setup(self, bot: _telebot.TeleBot) -> None:
        """Register Steeper hooks on a sync TeleBot instance.

        - Incoming: ``TeleBot.process_new_updates`` is wrapped so every update (with its real
          ``update_id`` and full payload) is forwarded to Steeper, for both polling and webhooks.
        - Outgoing: ``telebot.apihelper._make_request`` is wrapped (scoped to this bot's token)
          so API responses that contain full message objects are logged to Steeper.
        """
        _token_repos[bot.token] = self._repository
        _ensure_apihelper_patch()
        _wrap_process_new_updates(bot, self._repository)
        self._log_capture.start(self._repository.config, timeout=self._timeout)

        logger.info("Steeper middleware registered for pyTelegramBotAPI")

    def track(
        self,
        name: str,
        *,
        user_id: int,
        props: dict[str, Any] | None = None,
        ts: float | None = None,
    ) -> None:
        """Report one product event, for the platform to build funnels from.

        Synchronous and non-blocking: it buffers the event and returns, so it is
        safe to call from anywhere, including a hot handler.

        Steps like "finished onboarding" or "paid" never appear in Telegram
        traffic, so the bot has to say so itself::

            @bot.message_handler(commands=["buy"])
            def buy(message):
                steeper.track("checkout_started", user_id=message.from_user.id)

        Args:
            name: Event name, matched verbatim against a funnel's steps. Keep it
                stable — renaming an event breaks every funnel built on it.
            user_id: Telegram id of the user, i.e. the raw ``from_user.id``.
            props: Optional structured context. Stored, but not used for funnel
                matching, and neither indexed nor searchable yet.
            ts: Unix timestamp; defaults to now. Pass it only when replaying an
                event whose real time differs from the call.
        """
        self._repository.track(name, user_id=user_id, props=props, ts=ts)

    def close(self, *, timeout: float = 5.0) -> None:
        """Close the underlying HTTP client, blocking until it is done.

        pyTelegramBotAPI is synchronous and offers no shutdown hook, so this has to be
        called by hand — typically in a ``finally`` around ``bot.polling()``. Best-effort:
        it never raises.
        """
        self._log_capture.stop()
        # Flushed here rather than inside ``aclose`` below: shipping the last
        # events can take up to the client timeout, and ``timeout`` bounds the
        # whole call — routing it through there would abandon the flush that
        # matters most, the one holding the newest funnel steps.
        self._repository.tracker.close()
        run_threadsafe(self._repository.aclose(), timeout=timeout)

    @property
    def tracker(self) -> EventTracker:
        """The event tracker backing :meth:`track`.

        This, not the middleware, is what handlers should depend on. It knows
        nothing about Telegram or this framework — only ``track`` — so a handler
        taking it can be tested without an HTTP client or a dispatcher, and it
        drops into a DI container as an ordinary provider::

            dp = Dispatcher(tracker=steeper.tracker)

            async def buy(message: Message, tracker: EventTracker) -> None:
                tracker.track("checkout_started", user_id=message.from_user.id)

        :meth:`track` on the middleware is the shorthand for bots small enough
        not to want the wiring.
        """
        return self._repository.tracker

    @property
    def repository(self) -> SteeperRepository:
        return self._repository

    @property
    def client(self):
        """Compatibility alias for :attr:`repository.client`."""
        return self._repository.client
