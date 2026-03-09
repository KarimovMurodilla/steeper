from datetime import datetime, timezone
from uuid import UUID

from pydantic import Field, field_validator

from src.core.schemas import Base
from src.marketing.enums import BroadcastStatus


class BroadcastFilters(Base):
    """Optional filters for targeting broadcast recipients."""

    last_active_days: int | None = Field(
        None, description="Filter users active in the last N days", examples=[7]
    )


class BroadcastCreateRequest(Base):
    """Request body for POST /broadcasts."""

    bot_id: UUID = Field(
        ...,
        description="Target bot ID",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    text: str = Field(
        ..., description="Message text content", examples=["Special offer!"]
    )
    filters: BroadcastFilters | None = Field(
        None, description="Filters to target specific users"
    )
    schedule_at: datetime | None = Field(
        None, description="Scheduled time to send", examples=["2025-01-01T12:00:00Z"]
    )

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

    id: UUID = Field(
        ...,
        description="Broadcast UUID",
        examples=["123e4567-e89b-12d3-a456-426614174001"],
    )
    status: BroadcastStatus = Field(
        ...,
        description="Current status of the broadcast",
        examples=[BroadcastStatus.DRAFT],
    )


class BroadcastStatsResponse(Base):
    """Response for GET /broadcasts/{id}/stats."""

    total: int = Field(..., description="Total users targeted", examples=[1000])
    sent: int = Field(..., description="Successfully sent messages", examples=[950])
    failed: int = Field(..., description="Failed messages", examples=[50])
