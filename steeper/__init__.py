"""Steeper — Telegram bot middleware for the Steeper platform."""

__version__ = "0.1.0"


def __getattr__(name: str):
    if name == "SteeperConfig":
        from steeper._config import SteeperConfig
        return SteeperConfig
    if name == "SteeperClient":
        from steeper._client import SteeperClient
        return SteeperClient
    raise AttributeError(f"module 'steeper' has no attribute {name!r}")


__all__ = ["SteeperConfig", "SteeperClient"]
