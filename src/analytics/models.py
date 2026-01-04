from typing import Optional
from uuid import UUID as PY_UUID

from sqlalchemy import (
    ForeignKey,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import TimestampMixin, UUID7IDMixin


class AuditLog(Base, UUID7IDMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    admin_id: Mapped[PY_UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    bot_id: Mapped[Optional[PY_UUID]] = mapped_column(
        ForeignKey("bots.id"), nullable=True
    )

    action_type: Mapped[str] = mapped_column(String(100))
    target_entity: Mapped[str] = mapped_column(String(100))  # e.g. "broadcast", "user"
    target_id: Mapped[Optional[str]] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
