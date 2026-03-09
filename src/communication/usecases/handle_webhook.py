import time
from typing import Any
from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.communication.enums import ChatStatus, MessageType, SenderType
from src.communication.schemas import TelegramUpdatePayload
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import (
    AccessForbiddenException,
    InstanceNotFoundException,
)
from src.core.schemas import SuccessResponse
from src.realtime.broker import broker, steeper_exchange
from src.realtime.enums import EventType
from src.realtime.schemas import (
    WSChatCreatedData,
    WSChatMessageCreatedData,
    WSDownlinkEnvelope,
)

logger = get_logger(__name__)


class HandleWebhookUseCase:
    """
    Use case for processing incoming webhooks from Telegram or Middleware.
    It performs the following steps:
    1. Validates the bot token hash.
    2. Upserts the Telegram User (CRM).
    3. Gets or creates the Chat session.
    4. Saves the Message.
    5. Publishes events to Event Bus for real-time UI updates.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def _publish_chat_created(
        self,
        workspace_id: str,
        bot_id_str: str,
        chat_id_str: str,
        tg_user_data: dict[str, Any],
    ) -> None:
        """Publishes an event notifying that a new chat was created."""
        routing_key = (
            f"workspace.{workspace_id}.bot.{bot_id_str}.chat.{chat_id_str}.created"
        )

        chat_data = WSChatCreatedData(
            chat_id=chat_id_str,
            telegram_user=tg_user_data,
            status=ChatStatus.OPEN,
        )
        envelope = WSDownlinkEnvelope(
            version=1,
            event=EventType.CHAT_CREATED,
            workspace_id=workspace_id,
            bot_id=bot_id_str,
            chat_id=chat_id_str,
            timestamp=int(time.time()),
            data=chat_data.model_dump(mode="json"),
        )
        try:
            await broker.publish(
                envelope.model_dump(mode="json"),
                routing_key=routing_key,
                exchange=steeper_exchange,
            )
            logger.debug(
                "Published %s event to %s", EventType.CHAT_CREATED, routing_key
            )
        except Exception as e:
            logger.exception("Failed to publish CHAT_CREATED event to RabbitMQ: %s", e)

    async def _publish_message_created(
        self,
        workspace_id: str,
        bot_id_str: str,
        chat_id_str: str,
        message_id_str: str,
        tg_message_id: int,
        content: str,
        sender_type: SenderType,
    ) -> None:
        """Publishes an event notifying that a new message was received."""
        routing_key = f"workspace.{workspace_id}.bot.{bot_id_str}.chat.{chat_id_str}.message.created"
        message_data = WSChatMessageCreatedData(
            message_id=message_id_str,
            tg_message_id=tg_message_id,
            text=content,
            sender_type=sender_type,
        )
        envelope = WSDownlinkEnvelope(
            version=1,
            event=EventType.CHAT_MESSAGE_CREATED,
            workspace_id=workspace_id,
            bot_id=bot_id_str,
            chat_id=chat_id_str,
            timestamp=int(time.time()),
            data=message_data.model_dump(mode="json"),
        )
        try:
            await broker.publish(
                envelope.model_dump(mode="json"),
                routing_key=routing_key,
                exchange=steeper_exchange,
            )
            logger.debug(
                "Published %s event to %s", EventType.CHAT_MESSAGE_CREATED, routing_key
            )
        except Exception as e:
            logger.exception(
                "Failed to publish CHAT_MESSAGE_CREATED event to RabbitMQ: %s", e
            )

    async def execute(
        self, bot_id: UUID, payload: TelegramUpdatePayload, secret_token: str
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
            bot = await uow.bots.get_single(uow.session, id=bot_id)

            if not bot:
                logger.warning("Webhook received for unknown bot_id: %s", bot_id)
                raise InstanceNotFoundException(ErrorCode.BOT_NOT_FOUND)

            if bot.token_hash != secret_token:
                logger.warning(
                    "Webhook received with invalid secret token for bot: %s", bot_id
                )
                raise AccessForbiddenException(ErrorCode.AUTH_ACCESS_FORBIDDEN)

            if not bot.status == "active":
                logger.info("Webhook skipped for disabled bot: %s", bot.id)
                return SuccessResponse(success=True)

            tg_user_data = tg_msg.from_user.model_dump(by_alias=True)
            db_user = await uow.telegram_users.upsert(uow.session, bot.id, tg_user_data)
            chat = await uow.chats.get_by_tg_user(uow.session, bot.id, db_user.id)

            is_new_chat = False
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
                is_new_chat = True

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

            new_message = await uow.messages.create(uow.session, msg_data)

            await uow.session.flush()
            await uow.commit()

            logger.info(
                "Processed webhook for Bot %s, User %s, Msg %s",
                bot.id,
                db_user.tg_user_id,
                tg_msg.message_id,
            )

        workspace_id = str(bot.workspace_id)
        bot_id_str = str(bot.id)
        chat_id_str = str(chat.id)

        if is_new_chat:
            await self._publish_chat_created(
                workspace_id, bot_id_str, chat_id_str, tg_user_data
            )

        await self._publish_message_created(
            workspace_id,
            bot_id_str,
            chat_id_str,
            str(new_message.id),
            tg_msg.message_id,
            content,
            SenderType.USER,
        )

        return SuccessResponse(success=True)


def get_handle_webhook_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> HandleWebhookUseCase:
    return HandleWebhookUseCase(uow=uow)
