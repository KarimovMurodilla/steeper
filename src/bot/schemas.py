from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from src.bot.enums import BotStatus
from src.core.schemas import Base


class BotCreateRequest(Base):
    """Schema for creating a new bot."""

    name: str = Field(..., min_length=1, max_length=100)
    token: str = Field(..., min_length=10, description="Telegram Bot Token")

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("Invalid Telegram token format")
        return v


class BotUpdateRequest(Base):
    """Schema for updating bot settings."""

    name: str | None = Field(None, min_length=1, max_length=100)
    token: str | None = Field(None, description="New token if rotation is needed")
    status: BotStatus | None = None


class BotViewModel(Base):
    """Public view model for a Bot (excluding token)."""

    id: UUID
    workspace_id: UUID
    name: str
    status: BotStatus
    created_at: datetime


class BotSummaryViewModel(Base):
    """Simplified view model for lists."""

    id: UUID
    name: str
    status: BotStatus


class AdminBotRoleViewModel(Base):
    admin_id: UUID
    bot_id: UUID
    role_name: str
    permissions: dict[str, Any]


class AdminBotRoleAssignModel(Base):
    admin_id: UUID
    role_name: str
    permissions: dict[str, Any] = Field(default_factory=dict)
