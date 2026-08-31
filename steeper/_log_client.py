"""HTTP client for the log-ingestion endpoint.

Separate from :class:`~steeper._client.SteeperClient` on purpose. Updates and
outgoing messages are forwarded from the host's own event loop, while log
batches are shipped from the shared background loop, and an
``httpx.AsyncClient`` binds its connection pool to the loop it is first used
on. Sharing one client across both loops is exactly the kind of bug that shows
up only under load.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from steeper._config import SteeperConfig

logger = logging.getLogger("steeper")


class SteeperLogClient:
    """Posts batches of log records to the Steeper backend."""

    def __init__(self, config: SteeperConfig, *, timeout: float = 10.0) -> None:
        self._config = config
        self.timeout = timeout
        self._http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        # Created lazily so the client is bound to the loop that ships logs,
        # not to whichever loop happened to construct the handler.
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=self.timeout, verify=True)
        return self._http

    def _redact(self, message: str) -> str:
        """Strip the auth secret from text headed for the logs."""
        return message.replace(self._config.token_hash, "***")

    async def push(self, records: list[dict[str, Any]]) -> None:
        """POST one batch of log records. Never raises."""
        if not records:
            return
        try:
            resp = await self._client().post(
                self._config.logs_url,
                json={"records": records},
                headers={"x-telegram-bot-api-secret-token": self._config.token_hash},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            # Logged at DEBUG: this runs while shipping logs, and a WARNING per
            # failed batch would flood the very output the operator is reading.
            logger.debug("Steeper log shipping failed: %s", self._redact(str(exc)))

    async def aclose(self) -> None:
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
        self._http = None
