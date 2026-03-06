from enum import StrEnum

from pydantic import model_validator

from src.core.schemas import Base, TokenModel
from src.user.schemas import UserProfileViewModel


class TelegramAuthSource(StrEnum):
    WEBAPP = "webapp"
    LOGIN_WIDGET = "login_widget"


class TelegramLoginWidgetSchema(Base):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class TelegramAuthRequest(Base):
    source: TelegramAuthSource
    init_data: str | None = None
    telegram_login: TelegramLoginWidgetSchema | None = None

    @model_validator(mode="after")
    def validate_auth(self) -> "TelegramAuthRequest":
        if self.source == TelegramAuthSource.WEBAPP and not self.init_data:
            raise ValueError("init_data required")

        if self.source == TelegramAuthSource.LOGIN_WIDGET and not self.telegram_login:
            raise ValueError("telegram_login required")

        return self


class TelegramAuthResponse(Base):
    tokens: TokenModel
    user: UserProfileViewModel
