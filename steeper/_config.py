from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SteeperConfig:
    """Immutable configuration for the Steeper middleware.

    Args:
        base_url: Steeper backend URL (e.g. ``http://localhost:8000``).
        bot_id: UUID of the bot registered in Steeper.
        bot_token: Raw Telegram bot token from BotFather.
    """

    base_url: str
    bot_id: str
    bot_token: str

    @property
    def token_hash(self) -> str:
        """SHA-256 hex digest of the bot token, used by the backend for auth."""
        return hashlib.sha256(self.bot_token.encode()).hexdigest()

    @property
    def webhook_url(self) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/v1/communications/webhook/{self.bot_id}"

    @property
    def bot_message_url(self) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/v1/communications/webhook/{self.token_hash}/bot-message"
