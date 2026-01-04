
from fastapi import Depends

from loggers import get_logger
from src.communication.enums import ChatStatus, MessageType, SenderType
from src.communication.schemas import BotMessagePayload
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.schemas import SuccessResponse

logger = get_logger(__name__)


class LogBotMessageUseCase:
    """
    Use case for processing incoming webhooks from Telegram bot or Middleware.
    It performs the following steps:
    1. Validates the bot token hash.
    4. Saves the Message.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(
        self, token_hash: str, payload: BotMessagePayload
    ) -> SuccessResponse:
        async with self.uow as uow:
            bot = await uow.bots.get_by_token_hash(uow.session, token_hash)

            if not bot:
                logger.warning(
                    "Webhook received for unknown token hash: %s", token_hash
                )
                raise InstanceNotFoundException("Bot not found")

            if not bot.status == "active":
                logger.info("Webhook skipped for disabled bot: %s", bot.id)
                return SuccessResponse(success=True)
            
            tg_user = await uow.telegram_users.get_single(
                session=uow.session, tg_user_id=payload.chat_id, bot_id=bot.id
            )

            chat = await uow.chats.get_single(session=uow.session, bot_id=bot.id, telegram_user_id=tg_user.id)

            if not chat:
                chat = await uow.chats.create(
                    uow.session,
                    {
                        "bot_id": bot.id,
                        "telegram_user_id": payload.chat_id,
                        "status": ChatStatus.OPEN,
                    },
                )
                await uow.session.flush()

            msg_type = MessageType.TEXT # TODO: Determine message type based on payload

            msg_data = {
                "chat_id": chat.id,
                "sender_type": SenderType.BOT,
                "message_type": msg_type,
                "tg_message_id": payload.message_id,
                "content": payload.text,
                "metadata_info": {
                    "tg_date": payload.date,
                },
            }

            await uow.messages.create(uow.session, msg_data)

            await uow.commit()
            logger.info(
                "Processed webhook for Bot %s, User %s, Msg %s",
                bot.id,
                payload.chat_id,
                payload.text,
            )

        return SuccessResponse(success=True)


def get_log_bot_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> LogBotMessageUseCase:
    return LogBotMessageUseCase(uow=uow)
