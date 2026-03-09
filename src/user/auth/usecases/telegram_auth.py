from uuid import uuid4

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import (
    PermissionDeniedException,
    UnauthorizedException,
)
from src.core.redis.dependencies import get_redis_client
from src.user.auth.schemas import (
    TelegramAuthRequest,
    TelegramAuthResponse,
    TelegramAuthSource,
)
from src.user.auth.security import create_access_token, create_refresh_token
from src.user.auth.strategies.base import BaseAuthStrategy
from src.user.auth.strategies.telegram.dto import TelegramUserData
from src.user.auth.strategies.telegram.webapp import WebAppAuthStrategy
from src.user.auth.strategies.telegram.widget import LoginWidgetAuthStrategy
from src.user.schemas import UserProfileViewModel

logger = get_logger(__name__)


class TelegramAuthUseCase:
    """
    Orchestrator for Telegram authentication.
    Delegates validation and user resolution to specific injected strategies.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        redis_client: Redis,
        strategies: dict[
            TelegramAuthSource, BaseAuthStrategy[TelegramAuthRequest, TelegramUserData]
        ],
    ) -> None:
        self.uow = uow
        self.redis_client = redis_client
        self.strategies = strategies

    async def execute(self, data: TelegramAuthRequest) -> TelegramAuthResponse:
        strategy = self.strategies.get(data.source)
        if not strategy:
            logger.error(f"Unsupported auth source: {data.source}")
            raise UnauthorizedException(ErrorCode.AUTH_COULD_NOT_VALIDATE)

        user_data = strategy.verify(data)

        async with self.uow as uow:
            user = await strategy.resolve_user(uow, user_data)
            await uow.session.flush()

            logger.info(f"User resolved: {user.id}")

            if not user.is_active:
                logger.error(f"User is blocked: {user.id}")
                raise PermissionDeniedException(ErrorCode.USER_BLOCKED)

            token_data = {"sub": str(user.id)}
            session_id = str(uuid4())
            family = str(uuid4())

            access_token = await create_access_token(
                token_data, redis_client=self.redis_client, session_id=session_id
            )
            refresh_token = await create_refresh_token(
                token_data,
                redis_client=self.redis_client,
                session_id=session_id,
                family=family,
            )

            await uow.commit()

            logger.info(f"User authenticated: {user.id}")

            return TelegramAuthResponse(
                tokens={"access_token": access_token, "refresh_token": refresh_token},
                user=UserProfileViewModel.model_validate(user),
            )


def get_telegram_auth_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    redis_client: Redis = Depends(get_redis_client),
) -> TelegramAuthUseCase:
    strategies: dict[
        TelegramAuthSource, BaseAuthStrategy[TelegramAuthRequest, TelegramUserData]
    ] = {
        TelegramAuthSource.WEBAPP: WebAppAuthStrategy(),
        TelegramAuthSource.LOGIN_WIDGET: LoginWidgetAuthStrategy(),
    }

    return TelegramAuthUseCase(
        uow=uow,
        redis_client=redis_client,
        strategies=strategies,
    )
