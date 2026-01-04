
from fastapi import Depends

from loggers import get_logger
from src.communication.enums import ChatStatus, MessageType, SenderType
from src.communication.schemas import TelegramUpdatePayload
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.schemas import SuccessResponse

logger = get_logger(__name__)


class HandleWebhookUseCase:
    """
    Use case for processing incoming webhooks from Telegram or Middleware.
    It performs the following steps:
    1. Validates the bot token hash.
    2. Upserts the Telegram User (CRM).
    3. Gets or creates the Chat session.
    4. Saves the Message.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(
        self, token_hash: str, payload: TelegramUpdatePayload
    ) -> SuccessResponse:
        tg_msg = payload.message or payload.edited_message

        if not tg_msg:
            logger.debug("Received non-message update: %s", payload.update_id)
            return SuccessResponse(success=True)

        if not tg_msg.from_user:
            logger.debug(
                "Message without from_user (channel post?): %s", tg_msg.message_id
            )
            return SuccessResponse(success=True)

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

            tg_user_data = tg_msg.from_user.model_dump(by_alias=True)

            db_user = await uow.telegram_users.upsert(uow.session, bot.id, tg_user_data)

            chat = await uow.chats.get_by_tg_user(uow.session, bot.id, db_user.id)

            if not chat:
                chat = await uow.chats.create(
                    uow.session,
                    {
                        "bot_id": bot.id,
                        "telegram_user_id": db_user.id,
                        "status": ChatStatus.OPEN,
                    },
                )
                await uow.session.flush()

            content = tg_msg.text or tg_msg.caption or ""
            msg_type = MessageType.TEXT

            if not tg_msg.text and tg_msg.caption:
                msg_type = MessageType.MEDIA  # Simplified

            msg_data = {
                "chat_id": chat.id,
                "sender_type": SenderType.USER,
                "message_type": msg_type,
                "tg_message_id": tg_msg.message_id,
                "content": content,
                "metadata_info": {
                    "tg_date": tg_msg.date,
                },
            }

            await uow.messages.create(uow.session, msg_data)

            await uow.commit()
            logger.info(
                "Processed webhook for Bot %s, User %s, Msg %s",
                bot.id,
                db_user.tg_user_id,
                tg_msg.message_id,
            )

        return SuccessResponse(success=True)


def get_handle_webhook_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> HandleWebhookUseCase:
    return HandleWebhookUseCase(uow=uow)
