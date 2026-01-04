from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.bot.schemas import BotCreateRequest, BotViewModel
from src.bot.services.telegram_api import TelegramAPIService
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import (
    AccessForbiddenException,
)
from src.core.utils.encryption import encrypt_token
from src.core.utils.security import hash_token

logger = get_logger(__name__)


class CreateBotUseCase:
    """Use case for creating a new Telegram Bot in a workspace."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        tg_service: TelegramAPIService,
    ) -> None:
        self.uow = uow
        self.tg_service = tg_service

    async def execute(
        self,
        data: BotCreateRequest,
        user_id: UUID,
        workspace_id: UUID | None,
    ) -> BotViewModel:
        if not workspace_id:
            raise AccessForbiddenException(
                "Cannot create a bot without an active workspace context."
            )

        bot_info = await self.tg_service.get_me(data.token)
        if not bot_info:
            raise ValueError("Invalid Telegram Bot Token")

        async with self.uow as uow:
            token_hash = hash_token(data.token)
            token_encrypted = encrypt_token(data.token)

            bot_data = {
                "workspace_id": workspace_id,
                "name": data.name,
                "token_hash": token_hash,
                "token_encrypted": token_encrypted,
                "username": bot_info.username,
            }

            new_bot = await uow.bots.create(uow.session, bot_data)
            await uow.commit()

            logger.info(f"Bot created successfully: {new_bot.id} by Admin {user_id}")

            return BotViewModel.model_validate(new_bot)


def get_create_bot_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> CreateBotUseCase:
    return CreateBotUseCase(uow=uow, tg_service=TelegramAPIService())
