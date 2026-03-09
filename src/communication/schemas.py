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

    id: int = Field(
        ..., description="Unique identifier for this user or bot", examples=[123456789]
    )
    is_bot: bool = Field(
        ..., description="True, if this user is a bot", examples=[False]
    )
    first_name: str = Field(
        ..., description="User's or bot's first name", examples=["John"]
    )
    last_name: str | None = Field(
        None, description="User's or bot's last name", examples=["Doe"]
    )
    username: str | None = Field(
        None, description="User's or bot's username", examples=["johndoe"]
    )
    language_code: str | None = Field(
        None, description="IETF language tag of the user's language", examples=["en"]
    )


class TgChat(Base):
    """Represents a Telegram Chat."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(
        ..., description="Unique identifier for this chat", examples=[123456789]
    )
    type: str = Field(
        ...,
        description="Type of chat, can be either 'private', 'group', 'supergroup' or 'channel'",
        examples=["private"],
    )
    title: str | None = Field(
        None,
        description="Title, for supergroups, channels and group chats",
        examples=["My Supergroup"],
    )
    username: str | None = Field(
        None,
        description="Username, for private chats, supergroups and channels if available",
        examples=["my_supergroup"],
    )
    # For private chats (type='private'), Telegram includes first_name/last_name in the chat object
    first_name: str | None = Field(
        None,
        description="First name of the other party in a private chat",
        examples=["John"],
    )
    last_name: str | None = Field(
        None,
        description="Last name of the other party in a private chat",
        examples=["Doe"],
    )


class TgMessage(Base):
    """Represents a Telegram Message."""

    model_config = ConfigDict(extra="ignore")

    message_id: int = Field(
        ..., description="Unique message identifier inside this chat", examples=[1]
    )
    from_user: TgUser | None = Field(
        default=None,
        alias="from",
        description="Sender of the message, empty for messages sent to channels",
    )
    chat: TgChat = Field(..., description="Conversation the message belongs to")
    date: int = Field(
        ..., description="Date the message was sent in Unix time", examples=[1610000000]
    )
    text: str | None = Field(
        None,
        description="For text messages, the actual UTF-8 text of the message",
        examples=["Hello world!"],
    )
    caption: str | None = Field(
        None,
        description="Caption for the animation, audio, document, photo, video or voice",
        examples=["Check this out"],
    )

    # It is assumed that media fields are optional and can be ignored for now
    photo: list[Any] | None = Field(
        None, description="Message is a photo, available sizes of the photo"
    )
    document: Any | None = Field(
        None, description="Message is a general file, information about the file"
    )
    video: Any | None = Field(
        None, description="Message is a video, information about the video"
    )
    voice: Any | None = Field(
        None, description="Message is a voice message, information about the file"
    )


class TelegramUpdatePayload(Base):
    """
    Standard Telegram Update object.
    Matches the JSON structure sent by Telegram Webhooks or Aiogram Middleware.
    """

    model_config = ConfigDict(extra="ignore")

    update_id: int = Field(
        ..., description="The update's unique identifier", examples=[100000000]
    )
    message: TgMessage | None = Field(
        None, description="New incoming message of any kind"
    )
    edited_message: TgMessage | None = Field(
        None,
        description="New version of a message that is known to the bot and was edited",
    )
    # callback_query, channel_post, etc. can be added here later


class MessageViewModel(Base):
    """ViewModel for a saved message."""

    id: str = Field(
        ...,
        description="Message UUID",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    chat_id: str = Field(
        ..., description="Chat UUID", examples=["123e4567-e89b-12d3-a456-426614174001"]
    )
    sender_type: SenderType = Field(
        ..., description="Sender type (user or bot)", examples=[SenderType.USER]
    )
    message_type: MessageType = Field(
        ..., description="Message type", examples=[MessageType.TEXT]
    )
    content: str | None = Field(
        None, description="Message text content", examples=["Hello!"]
    )
    created_at: datetime = Field(
        ..., description="Creation timestamp", examples=["2025-01-01T12:00:00Z"]
    )


class BotMessagePayload(Base):
    """Payload when the bot itself sends a message via middleware."""

    chat_id: int = Field(..., description="Telegram Chat ID", examples=[123456789])
    text: str = Field(..., description="Message text", examples=["Bot reply text"])
    message_id: int = Field(..., description="Telegram Message ID", examples=[42])
    date: int = Field(..., description="Date sent in Unix time", examples=[1610000000])


class ChatListItemViewModel(Base):
    """GET /bots/{bot_id}/chats list item."""

    chat_id: UUID = Field(
        ...,
        description="Internal chat ID",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    telegram_id: int = Field(..., description="Telegram Chat ID", examples=[123456789])
    first_name: str | None = Field(
        None, description="First name of the user", examples=["John"]
    )
    username: str | None = Field(None, description="Username", examples=["johndoe"])
    last_message: str | None = Field(
        None, description="Text preview of the last message", examples=["Hello there"]
    )
    updated_at: datetime = Field(
        ..., description="Last message timestamp", examples=["2025-01-01T12:00:00Z"]
    )


class MessageListItemViewModel(Base):
    """GET /chats/{chat_id}/messages list item."""

    id: UUID = Field(
        ...,
        description="Internal message ID",
        examples=["123e4567-e89b-12d3-a456-426614174001"],
    )
    sender: SenderType = Field(
        ..., description="Sender type", examples=[SenderType.USER]
    )
    content: str | None = Field(
        None, description="Message text content", examples=["Hello"]
    )
    created_at: datetime = Field(
        ..., description="Message timestamp", examples=["2025-01-01T12:00:00Z"]
    )


class CursorPaginatedResponse(Base, Generic[T]):
    """Generic cursor-paginated response."""

    items: list[T] = Field(..., description="List of paginated items")
    next_cursor: str | None = Field(
        None,
        description="Cursor object for the next page, null if no more items",
        examples=["eyJjdXJzb3I..."],
    )


class SendMessageRequest(Base):
    """POST /chats/{chat_id}/messages request body."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Text of the message to be sent",
        examples=["Hello from the bot!"],
    )


class SendMessageResponse(Base):
    """POST /chats/{chat_id}/messages response."""

    telegram_message_id: int = Field(
        ..., description="Message ID returned by Telegram", examples=[43]
    )
    status: str = Field(
        "SENT", description="Status of the message delivery", examples=["SENT"]
    )
