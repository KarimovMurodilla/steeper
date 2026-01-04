from typing import TYPE_CHECKING, List, Optional
from uuid import UUID as PY_UUID

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base
from src.core.database.mixins import SoftDeleteMixin, TimestampMixin, UUIDIDMixin

if TYPE_CHECKING:
    from src.bot.models import Bot
    from src.communication.models import Chat


class TelegramUser(Base, UUIDIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "telegram_users"
    __table_args__ = (
        UniqueConstraint("tg_user_id", "bot_id", name="uq_tg_user_bot"),
        Index("idx_tg_user_bot", "tg_user_id", "bot_id"),
    )

    tg_user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Telegram ID > 2^32
    bot_id: Mapped[PY_UUID] = mapped_column(ForeignKey("bots.id"), nullable=False)

    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    bot: Mapped["Bot"] = relationship("Bot", back_populates="telegram_users")
    chats: Mapped[List["Chat"]] = relationship("Chat", back_populates="telegram_user")
