from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

logger = logging.getLogger("steeper")

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", ""})


@dataclass(frozen=True, slots=True)
class SteeperConfig:
    """Immutable configuration for the Steeper middleware.

    Args:
        base_url: Steeper backend URL (e.g. ``https://api.example.com``).
        bot_id: UUID of the bot registered in Steeper.
        bot_token: Raw Telegram bot token from BotFather.
    """

    base_url: str
    bot_id: str
    bot_token: str

    def __post_init__(self) -> None:
        parts = urlsplit(self.base_url)
        # Reject anything that is not a plain http(s) URL. This prevents the
        # backend URL from being abused to reach unexpected schemes/handlers
        # (``file://``, ``ftp://``, ``gopher://`` … which httpx or downstream
        # tooling could otherwise be coerced into following).
        if parts.scheme not in ("http", "https"):
            raise ValueError(
                f"base_url must use the http or https scheme, got {parts.scheme!r}"
            )
        if not parts.netloc:
            raise ValueError("base_url must include a host (e.g. https://host:port)")
        if not self.bot_id:
            raise ValueError("bot_id must not be empty")
        if not self.bot_token:
            raise ValueError("bot_token must not be empty")

        # Telegram message content (incl. user PII) and the auth secret are sent
        # to base_url. Over plaintext HTTP to a remote host that is trivially
        # interceptable, so warn loudly. localhost stays quiet for dev use.
        host = (parts.hostname or "").lower()
        if parts.scheme == "http" and host not in _LOCAL_HOSTS:
            logger.warning(
                "Steeper base_url uses plaintext HTTP to a non-local host (%s); "
                "message content and the auth token will be transmitted "
                "unencrypted. Use https:// in production.",
                host,
            )

    @property
    def token_hash(self) -> str:
        """SHA-256 hex digest of the bot token, used by the backend for auth."""
        return hashlib.sha256(self.bot_token.encode()).hexdigest()

    @property
    def _base(self) -> str:
        return self.base_url.rstrip("/")

    @property
    def webhook_url(self) -> str:
        return f"{self._base}/v1/communications/webhook/{quote(self.bot_id, safe='')}"

    @property
    def bot_message_url(self) -> str:
        return (
            f"{self._base}/v1/communications/webhook/"
            f"{quote(self.token_hash, safe='')}/bot-message"
        )

    def secret_matches(self, candidate: str) -> bool:
        """Constant-time comparison helper for the auth secret."""
        return hmac.compare_digest(self.token_hash, candidate)
