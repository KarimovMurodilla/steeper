import time
from uuid import UUID

from aiogram.types import Message
from fastapi import Depends
from sqlalchemy.orm import selectinload

from loggers import get_logger
from src.communication.enums import MessageType, SenderType
from src.communication.models import Chat
from src.communication.schemas import SendMessageRequest, SendMessageResponse
from src.core.database.session import get_unit_of_work
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import (
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.core.utils.encryption import decrypt_token
from src.integrations.telegram.bot.telegram_bot_api import TelegramBotAPIService
from src.integrations.telegram.dependencies import get_telegram_bot_api_service
from src.realtime.broker import broker, steeper_exchange
from src.realtime.enums import EventType
from src.realtime.schemas import WSChatMessageCreatedData, WSDownlinkEnvelope

logger = get_logger(__name__)


class SendMessageUseCase:
    """
    Sends a message to a Telegram user through the bot.

    Steps:
      1. Load chat with telegram_user and bot relationships.
      2. Decrypt the bot token.
      3. Call Telegram sendMessage API via httpx.
      4. Persist the outgoing message record.
      5. Publish event to Event Bus (RabbitMQ).
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        tg_bot_service: TelegramBotAPIService,
    ) -> None:
        self.uow = uow
        self.tg_bot_service = tg_bot_service

    async def execute(
        self,
        chat_id: UUID,
        data: SendMessageRequest,
    ) -> SendMessageResponse:
        async with self.uow as uow:
            chat = await uow.chats.get_single(
                uow.session,
                eager=[
                    selectinload(Chat.telegram_user),
                    selectinload(Chat.bot),
                ],
                id=chat_id,
            )
            if not chat:
                raise InstanceNotFoundException(ErrorCode.CHAT_NOT_FOUND)

            bot_token = decrypt_token(chat.bot.token_encrypted)
            tg_chat_id = chat.telegram_user.tg_user_id

            message = await self.tg_bot_service.send_message(
                token=bot_token,
                chat_id=tg_chat_id,
                text=data.text,
            )

            if bool(message) and isinstance(message, Message):
                tg_message_id = message.message_id
            else:
                raise InstanceProcessingException(ErrorCode.MESSAGE_SEND_FAILED)

            new_message = await uow.messages.create(
                uow.session,
                {
                    "chat_id": chat_id,
                    "sender_type": SenderType.ADMIN,
                    "message_type": MessageType.TEXT,
                    "tg_message_id": tg_message_id,
                    "content": data.text,
                    "metadata_info": {},
                },
            )

            await uow.session.flush()

            await uow.commit()

        workspace_id = str(chat.bot.workspace_id)
        bot_id_str = str(chat.bot_id)
        chat_id_str = str(chat_id)

        routing_key = f"workspace.{workspace_id}.bot.{bot_id_str}.chat.{chat_id_str}.message.created"

        message_data = WSChatMessageCreatedData(
            message_id=str(new_message.id),
            tg_message_id=tg_message_id,
            text=data.text,
            sender_type=SenderType.ADMIN,
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
            logger.exception("Failed to publish message event to RabbitMQ: %s", e)

        return SendMessageResponse(
            telegram_message_id=tg_message_id,
            status="SENT",
        )


def get_send_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    tg_bot_service: TelegramBotAPIService = Depends(get_telegram_bot_api_service),
) -> SendMessageUseCase:
    return SendMessageUseCase(uow=uow, tg_bot_service=tg_bot_service)
