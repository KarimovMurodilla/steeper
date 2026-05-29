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
import json
import logging
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
    orig = bot.process_new_updates

    def patched(updates: Any) -> Any:
        for update in updates or []:
            try:
                raw = _full_update_from_telebot(update)
            except Exception:
                logger.debug("Failed to build update payload", exc_info=True)
                continue
            _run_async(repository.forward_update(raw))
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
    ) -> None:
        self._repository = SteeperRepository(
            base_url=base_url,
            bot_id=bot_id,
            bot_token=bot_token,
            timeout=timeout,
        )

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

        logger.info("Steeper middleware registered for pyTelegramBotAPI")

    @property
    def repository(self) -> SteeperRepository:
        return self._repository

    @property
    def client(self):
        """Compatibility alias for :attr:`repository.client`."""
        return self._repository.client
