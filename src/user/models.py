from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base
from src.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDIDMixin,
)

if TYPE_CHECKING:
    from src.bot.models import AdminBotRole
    from src.workspace.models import WorkspaceMember


class User(Base, UUIDIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_telegram_id_active_not_deleted",
            "telegram_id",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "uq_users_username_not_deleted",
            "username",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    telegram_id: Mapped[int] = mapped_column(nullable=False)
    username: Mapped[str | None] = mapped_column(String(60), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    memberships: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="user", cascade="all, delete-orphan"
    )
    bot_roles: Mapped[list["AdminBotRole"]] = relationship(
        "AdminBotRole", back_populates="admin", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else str(self.telegram_id)
