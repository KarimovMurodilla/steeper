from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.bot.schemas import BotUpdateRequest, BotViewModel
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import CoreException, InstanceNotFoundException
from src.core.utils.encryption import encrypt_token
from src.core.utils.security import hash_token
from src.integrations.telegram.bot.telegram_bot_api import TelegramBotAPIService
from src.integrations.telegram.dependencies import get_telegram_bot_api_service
from src.main.config import config

logger = get_logger(__name__)


class UpdateBotUseCase:
    """Use case for updating a Telegram Bot's settings."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        tg_service: TelegramBotAPIService,
    ) -> None:
        self.uow = uow
        self.tg_service = tg_service

    async def _update_webhook(self, token_to_verify: str, result: BotViewModel) -> None:
        webhook_url = f"{config.telegram.TELEGRAM_WEBHOOK_URL}/{result.id}"
        is_webhook_set = await self.tg_service.set_webhook(
            token=token_to_verify,
            url=webhook_url,
            secret_token=hash_token(token_to_verify),
        )
        if not is_webhook_set:
            logger.warning(f"Webhook update failed for bot {result.id}")
        else:
            logger.info(f"Webhook updated successfully for bot {result.id}")

    async def execute(
        self,
        bot_id: UUID,
        workspace_id: UUID,
        data: BotUpdateRequest,
    ) -> BotViewModel:
        async with self.uow as uow:
            bot = await uow.bots.get_single(uow.session, id=bot_id)
            if not bot or bot.workspace_id != workspace_id:
                raise InstanceNotFoundException("Bot not found in the workspace.")

            update_data = data.model_dump(exclude_unset=True)

            should_update_webhook = False
            token_to_verify = data.token

            if data.token:
                bot_info = await self.tg_service.get_me(data.token)
                if not bot_info:
                    raise CoreException("Invalid new Telegram Bot Token")

                token_hash = hash_token(data.token)
                token_encrypted = encrypt_token(data.token)

                update_data["token_hash"] = token_hash
                update_data["token_encrypted"] = token_encrypted

                update_data["name"] = bot_info.first_name
                update_data["username"] = bot_info.username
                del update_data["token"]

                should_update_webhook = True

            if update_data:
                bot = await uow.bots.update(uow.session, update_data, id=bot_id)

            result = BotViewModel.model_validate(bot)

            await uow.commit()

        if should_update_webhook and token_to_verify:
            await self._update_webhook(token_to_verify, result)

        logger.info(f"Bot updated successfully: {result.id}")
        return result


def get_update_bot_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    tg_service: TelegramBotAPIService = Depends(get_telegram_bot_api_service),
) -> UpdateBotUseCase:
    return UpdateBotUseCase(uow=uow, tg_service=tg_service)
