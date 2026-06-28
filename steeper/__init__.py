"""Steeper — Telegram bot middleware for the Steeper platform."""

from typing import Any

__version__ = "0.1.3"


def __getattr__(name: str) -> Any:
    if name == "SteeperConfig":
        from steeper._config import SteeperConfig

        return SteeperConfig
    if name == "SteeperClient":
        from steeper._client import SteeperClient

        return SteeperClient
    if name == "SteeperRepository":
        from steeper.repository import SteeperRepository

        return SteeperRepository
    if name == "OutgoingMessageSnapshot":
        from steeper.repository import OutgoingMessageSnapshot

        return OutgoingMessageSnapshot
    raise AttributeError(f"module 'steeper' has no attribute {name!r}")


__all__ = ["SteeperConfig", "SteeperClient", "SteeperRepository", "OutgoingMessageSnapshot"]
