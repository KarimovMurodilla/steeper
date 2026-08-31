"""HTTP client for the product-event ingestion endpoint.

A third client, for the same reason there is a second one: event batches ship
from the shared background loop, and an ``httpx.AsyncClient`` binds its
connection pool to whichever loop first uses it. Sharing a pool across loops
fails only under load, which is the worst time to find out.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from steeper._config import SteeperConfig

logger = logging.getLogger("steeper")


class SteeperEventClient:
    """Posts batches of product events to the Steeper backend."""

    def __init__(self, config: SteeperConfig, *, timeout: float = 10.0) -> None:
        self._config = config
        self.timeout = timeout
        self._http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        # Created lazily so the client is bound to the loop that ships events,
        # not to whichever loop happened to construct the tracker.
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=self.timeout, verify=True)
        return self._http

    def _redact(self, message: str) -> str:
        """Strip the auth secret from text headed for the logs."""
        return message.replace(self._config.token_hash, "***")

    async def push(self, events: list[dict[str, Any]]) -> None:
        """POST one batch of events. Never raises.

        Failures are reported at WARNING, unlike log batches: a lost event is a
        permanently wrong funnel number, and nothing else will ever mention it.
        Log batches stay at DEBUG because warning about them would flood the
        very output being read; events have no such problem.
        """
        if not events:
            return
        try:
            resp = await self._client().post(
                self._config.events_url,
                json={"events": events},
                headers={"x-telegram-bot-api-secret-token": self._config.token_hash},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(
                "Steeper dropped a batch of %d events: %s",
                len(events),
                self._redact(str(exc)),
            )

    async def aclose(self) -> None:
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
        self._http = None
