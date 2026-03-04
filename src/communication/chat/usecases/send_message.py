"""Use case: send a message to a Telegram user via the bot's decrypted token."""

from uuid import UUID

from fastapi import Depends
import httpx
from sqlalchemy.orm import selectinload

from loggers import get_logger
from src.communication.enums import MessageType, SenderType
from src.communication.models import Chat
from src.communication.schemas import SendMessageRequest, SendMessageResponse
from src.core.database.session import get_unit_of_work
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork
from src.core.errors.exceptions import (
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.core.utils.encryption import decrypt_token
from src.main.config import config

logger = get_logger(__name__)


class SendMessageUseCase:
    """
    Sends a message to a Telegram user through the bot.

    Steps:
      1. Load chat with telegram_user and bot relationships.
      2. Decrypt the bot token.
      3. Call Telegram sendMessage API via httpx.
      4. Persist the outgoing message record.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

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
                raise InstanceNotFoundException("Chat not found.")

            bot_token = decrypt_token(chat.bot.token_encrypted)
            tg_chat_id = chat.telegram_user.tg_user_id

            url = f"{config.telegram.TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={"chat_id": tg_chat_id, "text": data.text},
                )

            if response.status_code != 200:
                logger.error(
                    "Telegram sendMessage failed: %s %s",
                    response.status_code,
                    response.text,
                )
                raise InstanceProcessingException(
                    f"Telegram API error: {response.status_code}"
                )

            tg_result = response.json().get("result", {})
            tg_message_id: int = tg_result.get("message_id", 0)

            # 4. Persist outgoing message
            await uow.messages.create(
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
            await uow.commit()

        return SendMessageResponse(
            telegram_message_id=tg_message_id,
            status="SENT",
        )


def get_send_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    # tg_bot_service: TelegramBotService = Depends(get_tg_bot_service),
) -> SendMessageUseCase:
    return SendMessageUseCase(uow=uow)
