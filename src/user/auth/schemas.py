from enum import StrEnum

from pydantic import Field, model_validator

from src.core.schemas import Base, TokenModel
from src.user.schemas import UserProfileViewModel


class TelegramAuthSource(StrEnum):
    WEBAPP = "webapp"
    LOGIN_WIDGET = "login_widget"


class TelegramLoginWidgetSchema(Base):
    id: int = Field(..., description="Telegram User ID", examples=[123456789])
    first_name: str = Field(..., description="User's first name", examples=["John"])
    last_name: str | None = Field(
        None, description="User's last name", examples=["Doe"]
    )
    username: str | None = Field(
        None, description="User's Telegram username", examples=["johndoe"]
    )
    photo_url: str | None = Field(
        None,
        description="User's profile photo URL",
        examples=["https://t.me/i/userpic/320/johndoe.jpg"],
    )
    auth_date: int = Field(
        ..., description="Authentication date in Unix time", examples=[1610000000]
    )
    hash: str = Field(..., description="Data authentication hash", examples=["d2...ce"])


class TelegramAuthRequest(Base):
    source: TelegramAuthSource = Field(
        ..., description="Authentication source", examples=[TelegramAuthSource.WEBAPP]
    )
    init_data: str | None = Field(
        None,
        description="Telegram WebApp initData string",
        examples=["query_id=...&user=...&hash=..."],
    )
    telegram_login: TelegramLoginWidgetSchema | None = Field(
        None, description="Telegram Login Widget data"
    )

    @model_validator(mode="after")
    def validate_auth(self) -> "TelegramAuthRequest":
        if self.source == TelegramAuthSource.WEBAPP and not self.init_data:
            raise ValueError("init_data required")

        if self.source == TelegramAuthSource.LOGIN_WIDGET and not self.telegram_login:
            raise ValueError("telegram_login required")

        return self


class TelegramAuthResponse(Base):
    tokens: TokenModel = Field(..., description="Access and Refresh tokens")
    user: UserProfileViewModel = Field(..., description="Authenticated user profile")
