from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.utils.encryption import decrypt_token
from src.integrations.telegram.bot.telegram_bot_api import TelegramBotAPIService
from src.integrations.telegram.dependencies import get_telegram_bot_api_service

logger = get_logger(__name__)


class DeleteBotUseCase:
    """Use case for deleting a Telegram Bot."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        tg_service: TelegramBotAPIService,
    ) -> None:
        self.uow = uow
        self.tg_service = tg_service

    async def execute(self, bot_id: UUID, workspace_id: UUID) -> None:
        async with self.uow as uow:
            bot = await uow.bots.get_single(uow.session, id=bot_id)
            if not bot or bot.workspace_id != workspace_id:
                raise InstanceNotFoundException(ErrorCode.BOT_NOT_FOUND)

            # decrypt token to remove webhook
            decrypted_token = decrypt_token(bot.token_encrypted)

            await uow.bots.delete(uow.session, id=bot_id)
            await uow.commit()

        # Try to delete webhook
        webhook_deleted = await self.tg_service.delete_webhook(token=decrypted_token)
        if not webhook_deleted:
            logger.warning(f"Failed to delete webhook for deleted bot {bot_id}")
        else:
            logger.info(f"Webhook deleted and bot {bot_id} removed")


def get_delete_bot_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    tg_service: TelegramBotAPIService = Depends(get_telegram_bot_api_service),
) -> DeleteBotUseCase:
    return DeleteBotUseCase(uow=uow, tg_service=tg_service)
