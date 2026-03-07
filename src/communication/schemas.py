from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import ConfigDict, Field

from src.communication.enums import MessageType, SenderType
from src.core.schemas import Base

T = TypeVar("T")


class TgUser(Base):
    """Represents a Telegram User from the API."""

    model_config = ConfigDict(extra="ignore")

    id: int
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class TgChat(Base):
    """Represents a Telegram Chat."""

    model_config = ConfigDict(extra="ignore")

    id: int
    type: str
    title: str | None = None
    username: str | None = None
    # For private chats (type='private'), Telegram includes first_name/last_name in the chat object
    first_name: str | None = None
    last_name: str | None = None


class TgMessage(Base):
    """Represents a Telegram Message."""

    model_config = ConfigDict(extra="ignore")

    message_id: int
    from_user: TgUser | None = Field(default=None, alias="from")
    chat: TgChat
    date: int
    text: str | None = None
    caption: str | None = None

    # It is assumed that media fields are optional and can be ignored for now
    photo: list[Any] | None = None
    document: Any | None = None
    video: Any | None = None
    voice: Any | None = None


class TelegramUpdatePayload(Base):
    """
    Standard Telegram Update object.
    Matches the JSON structure sent by Telegram Webhooks or Aiogram Middleware.
    """

    model_config = ConfigDict(extra="ignore")

    update_id: int
    message: TgMessage | None = None
    edited_message: TgMessage | None = None
    # callback_query, channel_post, etc. can be added here later


class MessageViewModel(Base):
    """ViewModel for a saved message."""

    id: str  # UUID
    chat_id: str  # UUID
    sender_type: SenderType
    message_type: MessageType
    content: str | None
    created_at: datetime


class BotMessagePayload(Base):
    """Payload when the bot itself sends a message via middleware."""

    chat_id: int  # Telegram Chat ID
    text: str
    message_id: int
    date: int


class ChatListItemViewModel(Base):
    """GET /bots/{bot_id}/chats list item."""

    chat_id: UUID
    telegram_id: int
    first_name: str | None = None
    username: str | None = None
    last_message: str | None = None
    updated_at: datetime


class MessageListItemViewModel(Base):
    """GET /chats/{chat_id}/messages list item."""

    id: UUID
    sender: SenderType
    content: str | None
    created_at: datetime


class CursorPaginatedResponse(Base, Generic[T]):
    """Generic cursor-paginated response."""

    items: list[T]
    next_cursor: str | None = None


class SendMessageRequest(Base):
    """POST /chats/{chat_id}/messages request body."""

    text: str = Field(..., min_length=1, max_length=4096)


class SendMessageResponse(Base):
    """POST /chats/{chat_id}/messages response."""

    telegram_message_id: int
    status: str = "SENT"
