from typing import Any

from pydantic import ConfigDict, Field

from src.communication.enums import ChatStatus, SenderType
from src.core.schemas import Base
from src.realtime.enums import EventType, WSAction


class WSUplinkMessage(Base):
    """Client → Server uplink action envelope."""

    model_config = ConfigDict(extra="allow")

    action: WSAction = Field(
        ..., description="Action to perform", examples=[WSAction.SUBSCRIBE]
    )
    token: str | None = Field(
        None, description="Auth token if authenticating", examples=["eyJhbG..."]
    )
    chat_id: str | None = Field(
        None,
        description="Chat ID if relevant to the action",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    bot_id: str | None = Field(
        None,
        description="Bot ID if relevant to the action",
        examples=["123e4567-e89b-12d3-a456-426614174001"],
    )


class WSDownlinkEnvelope(Base):
    """Server → Client downlink event envelope."""

    model_config = ConfigDict(extra="allow")

    version: int = Field(1, description="Protocol version", examples=[1])
    event: EventType = Field(
        ..., description="Event type", examples=[EventType.CHAT_MESSAGE_CREATED]
    )
    workspace_id: str = Field(
        ...,
        description="Workspace ID",
        examples=["123e4567-e89b-12d3-a456-426614174002"],
    )
    bot_id: str = Field(
        ..., description="Bot ID", examples=["123e4567-e89b-12d3-a456-426614174001"]
    )
    chat_id: str = Field(
        ..., description="Chat ID", examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    timestamp: int = Field(..., description="Unix timestamp", examples=[1610000000])
    data: dict[str, Any] = Field(..., description="Event payload data")


class WSErrorPayload(Base):
    """Error detail pushed to the client on system.error events."""

    code: int = Field(..., description="Error code", examples=[4000])
    message: str = Field(..., description="Error message", examples=["Invalid token"])


class WSChatCreatedData(Base):
    """Payload data for CHAT_CREATED event."""

    chat_id: str = Field(
        ..., description="Chat UUID", examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    telegram_user: dict[str, Any] = Field(..., description="Telegram user JSON object")
    status: ChatStatus = Field(
        ..., description="Chat status", examples=[ChatStatus.OPEN]
    )


class WSChatMessageCreatedData(Base):
    """Payload data for CHAT_MESSAGE_CREATED event."""

    message_id: str = Field(
        ...,
        description="Message UUID",
        examples=["123e4567-e89b-12d3-a456-426614174001"],
    )
    tg_message_id: int = Field(..., description="Telegram Message ID", examples=[43])
    text: str = Field(..., description="Message text content", examples=["Hello"])
    sender_type: SenderType = Field(
        ..., description="Sender type", examples=[SenderType.USER]
    )
