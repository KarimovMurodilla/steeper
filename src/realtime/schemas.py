from typing import Any

from pydantic import ConfigDict

from src.core.schemas import Base
from src.realtime.enums import EventType, WSAction


class WSUplinkMessage(Base):
    """Client → Server uplink action envelope."""

    model_config = ConfigDict(extra="allow")

    action: WSAction
    chat_id: str | None = None
    token: str | None = None


class WSDownlinkEnvelope(Base):
    """Server → Client downlink event envelope."""

    model_config = ConfigDict(extra="allow")

    version: int = 1
    event: EventType
    workspace_id: str
    bot_id: str
    chat_id: str
    timestamp: int
    data: dict[str, Any]


class WSErrorPayload(Base):
    """Error detail pushed to the client on system.error events."""

    code: int
    message: str
