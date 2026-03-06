from dataclasses import dataclass


@dataclass
class TelegramUserData:
    """DTO for normalized Telegram user data extracted from any auth source."""

    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    photo_url: str | None
    language_code: str | None = None
