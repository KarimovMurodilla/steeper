from typing import TYPE_CHECKING, List, Optional
from uuid import UUID as PY_UUID

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.communication.enums import ChatStatus, MessageType, SenderType
from src.core.database.base import Base
from src.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUID7IDMixin,
    UUIDIDMixin,
)

if TYPE_CHECKING:
    from src.bot.models import Bot
    from src.crm.models import TelegramUser


class Chat(Base, UUIDIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "chats"

    bot_id: Mapped[PY_UUID] = mapped_column(ForeignKey("bots.id"), nullable=False)
    telegram_user_id: Mapped[PY_UUID] = mapped_column(
        ForeignKey("telegram_users.id"), nullable=False
    )
    status: Mapped[ChatStatus] = mapped_column(
        SQLEnum(ChatStatus), default=ChatStatus.OPEN
    )

    # Relationships
    bot: Mapped["Bot"] = relationship("Bot", back_populates="chats")
    telegram_user: Mapped["TelegramUser"] = relationship(
        "TelegramUser", back_populates="chats"
    )
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="chat")


class Message(Base, UUID7IDMixin, TimestampMixin):
    __tablename__ = "messages"

    chat_id: Mapped[PY_UUID] = mapped_column(ForeignKey("chats.id"), nullable=False)
    sender_type: Mapped[SenderType] = mapped_column(SQLEnum(SenderType))
    message_type: Mapped[MessageType] = mapped_column(SQLEnum(MessageType))

    tg_message_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_info: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # For media_id, caption and etc.

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
