from datetime import datetime, timezone
from uuid import UUID

from pydantic import field_validator

from src.core.schemas import Base
from src.marketing.enums import BroadcastStatus


class BroadcastFilters(Base):
    """Optional filters for targeting broadcast recipients."""

    last_active_days: int | None = None


class BroadcastCreateRequest(Base):
    """Request body for POST /broadcasts."""

    bot_id: UUID
    text: str
    filters: BroadcastFilters | None = None
    schedule_at: datetime | None = None

    @field_validator("schedule_at")
    def validate_schedule_at(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            if v.tzinfo is not None:
                now = datetime.now(timezone.utc)
            else:
                now = datetime.now()

            if v < now:
                raise ValueError("schedule_at must not be in the past")
        return v


class BroadcastResponse(Base):
    """Response for broadcast creation."""

    id: UUID
    status: BroadcastStatus


class BroadcastStatsResponse(Base):
    """Response for GET /broadcasts/{id}/stats."""

    total: int
    sent: int
    failed: int
