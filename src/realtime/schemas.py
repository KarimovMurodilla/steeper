from typing import Any

from pydantic import ConfigDict

from src.communication.enums import ChatStatus, SenderType
from src.core.schemas import Base
from src.realtime.enums import EventType, WSAction


class WSUplinkMessage(Base):
    """Client → Server uplink action envelope."""

    model_config = ConfigDict(extra="allow")

    action: WSAction
    token: str | None = None
    chat_id: str | None = None
    bot_id: str | None = None


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


class WSChatCreatedData(Base):
    """Payload data for CHAT_CREATED event."""

    chat_id: str
    telegram_user: dict[str, Any]
    status: ChatStatus


class WSChatMessageCreatedData(Base):
    """Payload data for CHAT_MESSAGE_CREATED event."""

    message_id: str
    tg_message_id: int
    text: str
    sender_type: SenderType
