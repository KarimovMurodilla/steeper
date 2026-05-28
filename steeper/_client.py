from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from steeper._config import SteeperConfig

logger = logging.getLogger("steeper")


class SteeperClient:
    """Async HTTP client that forwards data to the Steeper backend."""

    def __init__(self, config: SteeperConfig, *, timeout: float = 10.0) -> None:
        self._config = config
        # verify defaults to True; keep it explicit so TLS validation is never
        # silently disabled by a future refactor.
        self._http = httpx.AsyncClient(timeout=timeout, verify=True)

    def _redact(self, message: str) -> str:
        """Strip the auth secret from text headed for the logs.

        The bot-message endpoint carries ``token_hash`` in its URL path, so a
        raw httpx error (which includes the request URL) would otherwise leak
        the auth secret into log files.
        """
        return message.replace(self._config.token_hash, "***")

    async def forward_update(self, update: dict[str, Any]) -> None:
        """POST a raw Telegram Update to the Steeper webhook endpoint."""
        try:
            resp = await self._http.post(
                self._config.webhook_url,
                json=update,
                headers={
                    "x-telegram-bot-api-secret-token": self._config.token_hash,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Steeper webhook failed: %s", self._redact(str(exc)))

    async def log_bot_message(
        self,
        chat_id: int,
        text: str,
        message_id: int,
        date: int | None = None,
    ) -> None:
        """POST a bot-sent message to the Steeper bot-message endpoint."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "message_id": message_id,
            "date": date or int(time.time()),
        }
        try:
            resp = await self._http.post(
                self._config.bot_message_url,
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Steeper bot-message log failed: %s", self._redact(str(exc)))

    async def close(self) -> None:
        await self._http.aclose()
