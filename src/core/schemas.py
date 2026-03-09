from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.core.utils.security import normalize_email
from src.core.validations import STRONG_PASSWORD_VALIDATOR


class Base(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, use_enum_values=True, extra="forbid"
    )


class IDSchema(Base):
    id: UUID = Field(
        ...,
        description="Unique identifier",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )


class TimestampSchema(Base):
    created_at: datetime = Field(
        ..., description="Creation timestamp", examples=["2025-01-01T12:00:00Z"]
    )
    updated_at: datetime | None = Field(
        None, description="Last update timestamp", examples=["2025-01-01T15:00:00Z"]
    )


class SuccessResponse(Base):
    success: bool = Field(
        ..., description="Indicates if the operation was successful", examples=[True]
    )


class TokenModel(Base):
    access_token: str = Field(
        ..., description="JWT access token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI..."]
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI..."],
    )


class EmailNormalizationMixin(BaseModel):
    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def _normalize_email(cls, v: str | EmailStr) -> str:
        return normalize_email(str(v))


class StrongPasswordValidationMixin(BaseModel):
    @field_validator("password", check_fields=False)
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not STRONG_PASSWORD_VALIDATOR.match(value):
            raise ValueError(
                "Password must contain at least one lowercase letter, one uppercase letter, one digit, one special character. Minimum length is 8 characters"
            )
        return value
