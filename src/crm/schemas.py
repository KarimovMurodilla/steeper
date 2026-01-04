from uuid import UUID

from src.core.schemas import Base, IDSchema, TimestampSchema


class TelegramUserBase(Base):
    tg_user_id: int
    first_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class TelegramUserRead(IDSchema, TimestampSchema, TelegramUserBase):
    bot_id: UUID


class TelegramUserFilter(Base):
    username: str | None = None
    has_username: bool | None = None
    language_code: str | None = None
    registered_after: str | None = None  # DateTime string
