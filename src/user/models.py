from typing import TYPE_CHECKING, List, Optional
from uuid import UUID as PY_UUID

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.core.database.base import Base
from src.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDIDMixin,
)
from src.core.utils.security import hash_password
from src.user.enums import SystemRole

if TYPE_CHECKING:
    from src.bot.models import AdminBotRole
    from src.workspace.models import Workspace


class User(Base, UUIDIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_email_active_not_deleted",
            "email",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    workspace_id: Mapped[Optional[PY_UUID]] = mapped_column(
        ForeignKey("workspaces.id"), nullable=True
    )

    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))

    # Global Platform Role (not bot specific)
    role: Mapped[SystemRole] = mapped_column(
        SQLEnum(SystemRole), nullable=False, default=SystemRole.MEMBER
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="users")
    bot_roles: Mapped[List["AdminBotRole"]] = relationship(
        "AdminBotRole", back_populates="admin"
    )

    @validates("password")
    def validate_password(self, _: str, value: str) -> str:
        if value != self.password:
            value = hash_password(value)
        return value

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
