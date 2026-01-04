from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from src.core.schemas import Base, IDSchema, TimestampSchema


class AuditLogSchemaBase(Base):
    admin_id: UUID = Field(..., description="ID of the admin who performed the action")
    bot_id: UUID | None = Field(
        None, description="ID of the bot associated with the action"
    )
    action_type: str = Field(
        ..., max_length=100, description="Type of action performed"
    )
    target_entity: str = Field(
        ...,
        max_length=100,
        description='Entity targeted by the action (e.g., "broadcast", "user")',
    )
    target_id: str | None = Field(
        None, max_length=100, description="ID of the target entity"
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
    admin_id: UUID
    action_type: str
    target_entity: str
    details: dict[str, Any]
    bot_id: UUID | None = None
    target_id: str | None = None


class AuditLogViewModel(IDSchema, TimestampSchema, AuditLogSchemaBase):
    pass
