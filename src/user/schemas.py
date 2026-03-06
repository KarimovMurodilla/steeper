from uuid import UUID

from src.core.schemas import Base


class UserProfileViewModel(Base):
    id: UUID
    telegram_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    photo_url: str | None = None


class UserSummaryViewModel(Base):
    id: UUID
    telegram_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class UserSummaryWithContactsViewModel(Base):
    id: UUID
    telegram_id: int
    full_name: str
    username: str | None = None
