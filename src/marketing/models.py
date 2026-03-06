from datetime import datetime
from typing import Any
from uuid import UUID as PY_UUID

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUID7IDMixin,
    UUIDIDMixin,
)
from src.marketing.enums import BroadcastStatus, DeliveryStatus


class Broadcast(Base, UUIDIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "broadcasts"

    bot_id: Mapped[PY_UUID] = mapped_column(ForeignKey("bots.id"), nullable=False)
    created_by: Mapped[PY_UUID] = mapped_column(ForeignKey("users.id"), nullable=True)

    message_content: Mapped[str] = mapped_column(Text)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[BroadcastStatus] = mapped_column(
        SQLEnum(BroadcastStatus), default=BroadcastStatus.DRAFT
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )


class BroadcastDelivery(Base, UUID7IDMixin, TimestampMixin):
    __tablename__ = "broadcast_deliveries"

    broadcast_id: Mapped[PY_UUID] = mapped_column(
        ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False
    )
    telegram_user_id: Mapped[PY_UUID] = mapped_column(
        ForeignKey("telegram_users.id"), nullable=False
    )
    status: Mapped[DeliveryStatus] = mapped_column(SQLEnum(DeliveryStatus))
