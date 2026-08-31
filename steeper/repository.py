"""Domain-facing API for syncing Telegram traffic with the Steeper backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from steeper._client import SteeperClient
from steeper._config import SteeperConfig
from steeper._events import EventTracker


@dataclass(frozen=True, slots=True)
class OutgoingMessageSnapshot:
    """Normalized outgoing bot message for Steeper logging."""

    chat_id: int
    message_id: int
    text: str
    date: int | None = None


def text_from_message_body(*, text: str | None, caption: str | None) -> str:
    """Prefer plain text, then caption (photos, documents, etc.)."""
    return (text or caption or "").strip()


class SteeperRepository:
    """Sync layer for Steeper: forwards incoming updates and records outgoing bot messages.

    Integrations should call :meth:`forward_update` for webhook-style incoming traffic and
    :meth:`record_outgoing` (or helpers that build :class:`OutgoingMessageSnapshot`) for every
    bot-originated message you want mirrored to Steeper.

    :meth:`track` is the third channel and the only one the bot's own code drives:
    Telegram traffic cannot say that a user finished onboarding or paid, so the bot
    reports those steps itself and the platform builds funnels from them.
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
    ) -> None:
        self._config = SteeperConfig(
            base_url=base_url,
            bot_id=bot_id,
            bot_token=bot_token,
        )
        self._client = SteeperClient(self._config, timeout=timeout)
        # Cheap to build: no thread and no connection until the first event.
        self._tracker = EventTracker(
            self._config,
            batch_size=event_batch_size,
            flush_interval=event_flush_interval,
            timeout=timeout,
        )

    @property
    def config(self) -> SteeperConfig:
        return self._config

    @property
    def client(self) -> SteeperClient:
        """Low-level HTTP client (same instance integrations have always used)."""
        return self._client

    @property
    def tracker(self) -> EventTracker:
        """The event tracker backing :meth:`track`."""
        return self._tracker

    async def forward_update(self, update: dict[str, Any]) -> None:
        """POST a raw Telegram update JSON to Steeper."""
        await self._client.forward_update(update)

    async def record_outgoing(self, snapshot: OutgoingMessageSnapshot) -> None:
        """Log a single outgoing bot message to Steeper."""
        await self._client.log_bot_message(
            chat_id=snapshot.chat_id,
            text=snapshot.text,
            message_id=snapshot.message_id,
            date=snapshot.date,
        )

    def track(
        self,
        name: str,
        *,
        user_id: int,
        props: dict[str, Any] | None = None,
        ts: float | None = None,
    ) -> None:
        """Report one product event. Synchronous, non-blocking, never raises.

        Not a coroutine, and deliberately so: it only appends to a buffer, and
        making it awaitable would imply the bot should wait for something.
        Call it the same way from an async handler and a telebot worker thread.

        Args:
            name: Event name, matched verbatim against a funnel's steps. Keep it
                stable — renaming an event breaks every funnel built on it.
            user_id: Telegram id of the user, i.e. the raw ``from_user.id``.
            props: Optional structured context. Stored, but not used for funnel
                matching, and neither indexed nor searchable yet.
            ts: Unix timestamp; defaults to now. Pass it only when replaying an
                event whose real time differs from the call.
        """
        self._tracker.track(name, user_id=user_id, props=props, ts=ts)

    async def aclose(self) -> None:
        await self._tracker.aclose()
        await self._client.close()
