from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from src.bot.enums import BotRole, BotStatus
from src.core.schemas import Base


class BotCreateRequest(Base):
    """Schema for creating a new bot."""

    token: str = Field(
        ...,
        min_length=10,
        description="Telegram bot token obtained from BotFather",
        examples=["1234567890:ABCdef123ghi456jklmNOpqrSTUvwxyz"],
    )

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("Invalid Telegram token format")
        return v


class BotUpdateRequest(Base):
    """Schema for updating bot settings."""

    token: str | None = Field(
        None,
        description="New token if rotation is needed",
        examples=["1234567890:ABCdef123ghi456jklmNOpqrSTUvwxyz"],
    )
    status: BotStatus | None = Field(
        None, description="Current status of the bot", examples=[BotStatus.ACTIVE]
    )


class BotViewModel(Base):
    """Public view model for a Bot (excluding token)."""

    id: UUID = Field(
        ...,
        description="Unique bot identifier",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    workspace_id: UUID = Field(
        ...,
        description="Workspace ID where the bot belongs",
        examples=["123e4567-e89b-12d3-a456-426614174001"],
    )
    name: str = Field(..., description="Name of the bot", examples=["Support Bot"])
    status: BotStatus = Field(
        ..., description="Current status of the bot", examples=[BotStatus.ACTIVE]
    )
    created_at: datetime = Field(
        ...,
        description="Date and time when bot was created",
        examples=["2025-01-01T12:00:00Z"],
    )


class BotSummaryViewModel(Base):
    """Simplified view model for lists."""

    id: UUID = Field(
        ...,
        description="Unique bot identifier",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    name: str = Field(..., description="Name of the bot", examples=["Support Bot"])
    status: BotStatus = Field(
        ..., description="Current status of the bot", examples=[BotStatus.ACTIVE]
    )


class AdminBotRoleViewModel(Base):
    admin_id: UUID = Field(
        ...,
        description="Unique admin identifier",
        examples=["123e4567-e89b-12d3-a456-426614174002"],
    )
    bot_id: UUID = Field(
        ...,
        description="Unique bot identifier",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    role: BotRole = Field(
        ..., description="Role assigned to admin", examples=[BotRole.ADMIN]
    )


class AdminBotRoleAssignRequest(Base):
    """Request body for POST /bots/{bot_id}/admins."""

    user_id: UUID = Field(
        ...,
        description="User ID to grant access to",
        examples=["123e4567-e89b-12d3-a456-426614174002"],
    )
    role: BotRole = Field(..., description="Role to assign", examples=[BotRole.ADMIN])
