from typing import TYPE_CHECKING, List

from sqlalchemy import (
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base
from src.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDIDMixin,
)

if TYPE_CHECKING:
    from src.bot.models import Bot
    from src.user.models import User


class Workspace(Base, UUIDIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    bots: Mapped[List["Bot"]] = relationship("Bot", back_populates="workspace")
    users: Mapped[List["User"]] = relationship("User", back_populates="workspace")

    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, name={self.name})>"
