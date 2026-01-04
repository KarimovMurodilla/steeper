from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.core.database.base import Base
from src.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDIDMixin,
)
from src.core.utils.security import hash_password

if TYPE_CHECKING:
    from src.bot.models import AdminBotRole
    from src.workspace.models import WorkspaceMember


class User(Base, UUIDIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_email_active_not_deleted",
            "email",
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

    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(60))
    phone_number: Mapped[str] = mapped_column(String(20))
    password: Mapped[str] = mapped_column(String(255))

    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    memberships: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="user", cascade="all, delete-orphan"
    )
    bot_roles: Mapped[list["AdminBotRole"]] = relationship(
        "AdminBotRole", back_populates="admin", cascade="all, delete-orphan"
    )

    @validates("password")
    def validate_password(self, _: str, value: str) -> str:
        if value != self.password:
            value = hash_password(value)
        return value

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
