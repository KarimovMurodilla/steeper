import hashlib
import hmac
import time

from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import (
    PermissionDeniedException,
    UnauthorizedException,
)
from src.main.config import config
from src.user.auth.schemas import TelegramAuthRequest
from src.user.auth.strategies.base import BaseAuthStrategy
from src.user.auth.strategies.telegram.dto import TelegramUserData
from src.user.models import User


class LoginWidgetAuthStrategy(BaseAuthStrategy[TelegramAuthRequest, TelegramUserData]):
    """Strategy for Telegram Login Widget authentication."""

    def verify(self, data: TelegramAuthRequest) -> TelegramUserData:
        login_data = data.telegram_login
        if not login_data:
            raise UnauthorizedException(ErrorCode.AUTH_TELEGRAM_DATA_REQUIRED)

        if time.time() - login_data.auth_date > 86400:
            raise UnauthorizedException(ErrorCode.AUTH_TELEGRAM_DATA_OUTDATED)

        data_dict = login_data.model_dump(exclude={"hash"}, exclude_none=True)
        received_hash = login_data.hash

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()))

        secret_key = hashlib.sha256(
            config.telegram.TELEGRAM_BOT_TOKEN.encode()
        ).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            raise UnauthorizedException(ErrorCode.AUTH_TELEGRAM_HASH_MISMATCH)

        return TelegramUserData(
            telegram_id=login_data.id,
            first_name=login_data.first_name,
            last_name=login_data.last_name,
            username=login_data.username,
            photo_url=login_data.photo_url,
            language_code=None,
        )

    async def resolve_user(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        user_data: TelegramUserData,
    ) -> User:
        user = await uow.users.get_single(
            uow.session, telegram_id=user_data.telegram_id
        )

        if not user:
            raise PermissionDeniedException(ErrorCode.AUTH_PERMISSION_DENIED)

        has_workspaces = await uow.workspace_members.exists(
            uow.session, user_id=user.id
        )
        if not has_workspaces:
            raise PermissionDeniedException(ErrorCode.AUTH_PERMISSION_DENIED)

        user.first_name = user_data.first_name
        user.username = user_data.username
        if user_data.last_name:
            user.last_name = user_data.last_name
        if user_data.photo_url:
            user.photo_url = user_data.photo_url

        return user
