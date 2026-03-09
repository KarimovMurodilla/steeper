from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from src.core.schemas import Base, IDSchema, TimestampSchema


class AuditLogSchemaBase(Base):
    admin_id: UUID = Field(
        ...,
        description="ID of the admin who performed the action",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    bot_id: UUID | None = Field(
        None,
        description="ID of the bot associated with the action",
        examples=["123e4567-e89b-12d3-a456-426614174001"],
    )
    action_type: str = Field(
        ...,
        max_length=100,
        description="Type of action performed",
        examples=["SEND_MESSAGE"],
    )
    target_entity: str = Field(
        ...,
        max_length=100,
        description='Entity targeted by the action (e.g., "broadcast", "user")',
        examples=["broadcast"],
    )
    target_id: str | None = Field(
        None,
        max_length=100,
        description="ID of the target entity",
        examples=["123e4567-e89b-12d3-a456-426614174002"],
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details about the action in JSON format",
    )

    @field_validator("action_type", "target_entity", "target_id")
    def validate_string_fields(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
        return v


class CreateAuditLogModel(AuditLogSchemaBase):
    admin_id: UUID = Field(
        ..., description="Admin ID", examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    action_type: str = Field(
        ..., description="Type of action", examples=["SEND_MESSAGE"]
    )
    target_entity: str = Field(..., description="Target entity", examples=["user"])
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Action details JSON",
        examples=[{"status": "success"}],
    )
    bot_id: UUID | None = Field(
        None, description="Bot ID", examples=["123e4567-e89b-12d3-a456-426614174001"]
    )
    target_id: str | None = Field(
        None, description="Target ID", examples=["123e4567-e89b-12d3-a456-426614174002"]
    )


class AuditLogViewModel(IDSchema, TimestampSchema, AuditLogSchemaBase):
    pass


class BotAnalyticsSummary(Base):
    """Response for GET /bots/{bot_id}/analytics/summary."""

    users: int = Field(
        ..., description="Total unique Telegram users of this bot", examples=[1500]
    )
    chats: int = Field(..., description="Total chat sessions", examples=[302])
    messages: int = Field(
        ..., description="Total messages in all chats", examples=[45000]
    )
    dau: int = Field(
        ...,
        description="Daily active users (sent/received a message today)",
        examples=[150],
    )


class AuditLogListItemViewModel(Base):
    """Single item in GET /audit-logs response."""

    actor: str = Field(
        ...,
        description="Telegram ID of the admin who performed the action",
        examples=["123456789"],
    )
    action: str = Field(
        ..., description="Action type (e.g. SEND_MESSAGE)", examples=["SEND_MESSAGE"]
    )
    created_at: datetime = Field(
        ..., description="Creation timestamp", examples=["2025-01-01T12:00:00Z"]
    )
