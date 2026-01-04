from datetime import datetime
from typing import Optional, Any

from pydantic import Field, ConfigDict

from src.communication.enums import MessageType, SenderType
from src.core.schemas import Base


class TgUser(Base):
    """Represents a Telegram User from the API."""
    model_config = ConfigDict(extra='ignore')

    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None


class TgChat(Base):
    """Represents a Telegram Chat."""
    model_config = ConfigDict(extra='ignore')

    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    # For private chats (type='private'), Telegram includes first_name/last_name in the chat object
    first_name: Optional[str] = None 
    last_name: Optional[str] = None


class TgMessage(Base):
    """Represents a Telegram Message."""
    model_config = ConfigDict(extra='ignore')

    message_id: int
    from_user: Optional[TgUser] = Field(default=None, alias="from_user")
    chat: TgChat
    date: int
    text: Optional[str] = None
    caption: Optional[str] = None
    
    # It is assumed that media fields are optional and can be ignored for now
    photo: Optional[list[Any]] = None
    document: Optional[Any] = None
    video: Optional[Any] = None
    voice: Optional[Any] = None


class TelegramUpdatePayload(Base):
    """
    Standard Telegram Update object.
    Matches the JSON structure sent by Telegram Webhooks or Aiogram Middleware.
    """
    model_config = ConfigDict(extra='ignore')

    update_id: int
    message: Optional[TgMessage] = None
    edited_message: Optional[TgMessage] = None
    # callback_query, channel_post, etc. can be added here later


class MessageViewModel(Base):
    """ViewModel for a saved message."""
    id: str  # UUID
    chat_id: str  # UUID
    sender_type: SenderType
    message_type: MessageType
    content: Optional[str]
    created_at: datetime


class BotMessagePayload(Base):
    """Payload when the bot itself sends a message via middleware."""
    chat_id: int # Telegram Chat ID
    text: str
    message_id: int
    date: int
