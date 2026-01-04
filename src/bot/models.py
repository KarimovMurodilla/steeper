from typing import TYPE_CHECKING, List
from uuid import UUID as PY_UUID

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.bot.enums import BotRole, BotStatus
from src.core.database.base import Base
from src.core.database.mixins import SoftDeleteMixin, TimestampMixin, UUIDIDMixin

if TYPE_CHECKING:
    from src.communication.models import Chat
    from src.crm.models import TelegramUser
    from src.user.models import User
    from src.workspace.models import Workspace


class Bot(Base, UUIDIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "bots"

    workspace_id: Mapped[PY_UUID] = mapped_column(
        ForeignKey("workspaces.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100), unique=True)
    token_hash: Mapped[str] = mapped_column(String(255))
    token_encrypted: Mapped[str] = mapped_column(String(1000))
    status: Mapped[BotStatus] = mapped_column(
        SQLEnum(BotStatus), default=BotStatus.ACTIVE
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="bots")
    telegram_users: Mapped[List["TelegramUser"]] = relationship(
        "TelegramUser", back_populates="bot"
    )
    chats: Mapped[List["Chat"]] = relationship("Chat", back_populates="bot")
    admin_roles: Mapped[List["AdminBotRole"]] = relationship(
        "AdminBotRole", back_populates="bot"
    )


class AdminBotRole(Base, UUIDIDMixin, TimestampMixin):
    __tablename__ = "admin_bot_roles"
    __table_args__ = (UniqueConstraint("admin_id", "bot_id", name="uq_admin_bot_role"),)

    admin_id: Mapped[PY_UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    bot_id: Mapped[PY_UUID] = mapped_column(ForeignKey("bots.id"), nullable=False)
    role: Mapped[BotRole] = mapped_column(
        SQLEnum(BotRole), nullable=False, default=BotRole.VIEWER
    )
    permissions: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # Extensible permissions

    # Relationships
    admin: Mapped["User"] = relationship("User", back_populates="bot_roles")
    bot: Mapped["Bot"] = relationship("Bot", back_populates="admin_roles")
