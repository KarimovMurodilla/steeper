from uuid import UUID

from loggers import get_logger
from src.bot.enums import BotRole
from src.bot.schemas import BotCreateRequest, BotViewModel
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import (
    AccessForbiddenException,
    CoreException,
)
from src.core.utils.encryption import encrypt_token
from src.core.utils.security import hash_token
from src.integrations.telegram.bot.telegram_bot_api import TelegramBotAPIService
from src.main.config import config

logger = get_logger(__name__)


class CreateBotUseCase:
    """Use case for creating a new Telegram Bot in a workspace."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        tg_service: TelegramBotAPIService,
    ) -> None:
        self.uow = uow
        self.tg_service = tg_service

    async def execute(
        self,
        data: BotCreateRequest,
        user_id: UUID,
        workspace_id: UUID | None,
    ) -> BotViewModel:
        """
        Executes the business logic for creating a new Telegram Bot.

        Args:
            data (BotCreateRequest): The payload containing bot details.
            user_id (UUID): The unique identifier of the user creating the bot.
            workspace_id (UUID | None): The current workspace ID.

        Returns:
            BotViewModel: The created bot details.

        Raises:
            AccessForbiddenException: If the user lacks workspace access.
            CoreException: If the provided bot token is invalid.
        """
        if not workspace_id:
            raise AccessForbiddenException(ErrorCode.WORKSPACE_ACCESS_DENIED)

        bot_info = await self.tg_service.get_me(data.token)
        if not bot_info:
            raise CoreException(ErrorCode.AUTH_TOKEN_INVALID)

        async with self.uow as uow:
            token_hash = hash_token(data.token)
            token_encrypted = encrypt_token(data.token)

            bot_data = {
                "workspace_id": workspace_id,
                "name": bot_info.first_name,
                "token_hash": token_hash,
                "token_encrypted": token_encrypted,
                "username": bot_info.username,
            }

            new_bot = await uow.bots.create(uow.session, bot_data)

            await uow.session.flush()

            await uow.admin_bot_roles.create(
                uow.session,
                {
                    "admin_id": user_id,
                    "bot_id": new_bot.id,
                    "role": BotRole.ADMIN,
                },
            )
            await uow.session.refresh(new_bot, ["admin_roles"])

            result = BotViewModel.model_validate(new_bot)

            await uow.commit()

        webhook_url = f"{config.telegram.TELEGRAM_WEBHOOK_URL}/{result.id}"
        is_webhook_set = await self.tg_service.set_webhook(
            token=data.token,
            url=webhook_url,
            secret_token=token_hash,
        )
        if not is_webhook_set:
            logger.warning(f"Webhook setup failed for bot {result.id}")
        else:
            logger.info(f"Webhook set successfully for bot {result.id}")

        logger.info(f"Bot created successfully: {result.id} by Admin {user_id}")

        return result
