"""Domain-facing API for syncing Telegram traffic with the Steeper backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from steeper._client import SteeperClient
from steeper._config import SteeperConfig


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

    @property
    def config(self) -> SteeperConfig:
        return self._config

    @property
    def client(self) -> SteeperClient:
        """Low-level HTTP client (same instance integrations have always used)."""
        return self._client

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

    async def aclose(self) -> None:
        await self._client.close()
