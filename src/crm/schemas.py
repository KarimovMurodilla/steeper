from uuid import UUID

from pydantic import Field

from src.core.schemas import Base, IDSchema, TimestampSchema


class TelegramUserBase(Base):
    tg_user_id: int = Field(..., description="Telegram User ID", examples=[123456789])
    first_name: str | None = Field(
        None, description="User's first name", examples=["John"]
    )
    username: str | None = Field(
        None, description="User's username", examples=["john_doe"]
    )
    language_code: str | None = Field(
        None, description="User's language code", examples=["en"]
    )


class TelegramUserRead(IDSchema, TimestampSchema, TelegramUserBase):
    bot_id: UUID = Field(
        ...,
        description="Associated bot ID",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )


class TelegramUserFilter(Base):
    username: str | None = Field(
        None, description="Filter by username", examples=["john_doe"]
    )
    has_username: bool | None = Field(
        None, description="Filter users with/without username", examples=[True]
    )
    language_code: str | None = Field(
        None, description="Filter by language code", examples=["en"]
    )
    registered_after: str | None = Field(
        None,
        description="Filter by registration date",
        examples=["2025-01-01T00:00:00Z"],
    )
