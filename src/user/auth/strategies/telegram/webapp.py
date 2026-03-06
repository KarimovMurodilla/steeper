import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import UnauthorizedException
from src.main.config import config
from src.user.auth.schemas import TelegramAuthRequest
from src.user.auth.strategies.base import BaseAuthStrategy
from src.user.auth.strategies.telegram.dto import TelegramUserData
from src.user.models import User


class WebAppAuthStrategy(BaseAuthStrategy[TelegramAuthRequest, TelegramUserData]):
    """Strategy for Telegram WebApp authentication."""

    def verify(self, data: TelegramAuthRequest) -> TelegramUserData:
        if not data.init_data:
            raise UnauthorizedException("init_data is required for WebApp auth")

        parsed_data = dict(parse_qsl(data.init_data, keep_blank_values=True))
        if "hash" not in parsed_data:
            raise UnauthorizedException("INVALID_TELEGRAM_SIGNATURE")

        received_hash = parsed_data.pop("hash")
        auth_date = int(parsed_data.get("auth_date", 0))

        if time.time() - auth_date > 86400:
            raise UnauthorizedException("TELEGRAM_AUTH_EXPIRED")

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )

        secret_key = hmac.new(
            b"WebAppData", config.telegram.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            raise UnauthorizedException("INVALID_TELEGRAM_SIGNATURE")

        user_dict = json.loads(parsed_data.get("user", "{}"))
        return TelegramUserData(
            telegram_id=user_dict.get("id"),
            first_name=user_dict.get("first_name", ""),
            last_name=user_dict.get("last_name"),
            username=user_dict.get("username"),
            language_code=user_dict.get("language_code"),
            photo_url=user_dict.get("photo_url"),
        )

    async def resolve_user(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        user_data: TelegramUserData,
    ) -> User:
        user = await uow.users.get_single(
            uow.session, telegram_id=user_data.telegram_id
        )

        if user:
            user.first_name = user_data.first_name
            if user_data.last_name:
                user.last_name = user_data.last_name
            user.username = user_data.username
            if user_data.language_code:
                user.language_code = user_data.language_code
            if user_data.photo_url:
                user.photo_url = user_data.photo_url
        else:
            user = await uow.users.create(
                uow.session,
                {
                    "telegram_id": user_data.telegram_id,
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name or "",
                    "username": user_data.username,
                    "language_code": user_data.language_code,
                    "photo_url": user_data.photo_url,
                },
            )
        return user
