from typing import TYPE_CHECKING, List
from uuid import UUID as PY_UUID

from sqlalchemy import (
    ForeignKey,
    String,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base
from src.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDIDMixin,
)
from src.workspace.enums import WorkspaceRole

if TYPE_CHECKING:
    from src.bot.models import Bot
    from src.user.models import User


class Workspace(Base, UUIDIDMixin, TimestampMixin):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="workspace"
    )
    bots: Mapped[List["Bot"]] = relationship(
        "Bot", back_populates="workspace"
    )


class WorkspaceMember(Base, UUIDIDMixin, TimestampMixin):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint('user_id', 'workspace_id', name='uq_workspace_member'),
    )

    user_id: Mapped[PY_UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    workspace_id: Mapped[PY_UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    
    role: Mapped[WorkspaceRole] = mapped_column(
        SQLEnum(WorkspaceRole), nullable=False, default=WorkspaceRole.MEMBER
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
