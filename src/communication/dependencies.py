"""Communication-module shared dependencies."""

from fastapi import Depends

from src.communication.chat.usecases.list_chats import ListChatsUseCase
from src.communication.chat.usecases.list_messages import ListMessagesUseCase
from src.communication.chat.usecases.send_message import SendMessageUseCase
from src.communication.usecases.handle_webhook import HandleWebhookUseCase
from src.communication.usecases.log_bot_message import LogBotMessageUseCase
from src.core.database.session import get_unit_of_work
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork
from src.integrations.telegram.bot.telegram_bot_api import TelegramBotAPIService
from src.integrations.telegram.dependencies import get_telegram_bot_api_service


def get_list_chats_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListChatsUseCase:
    return ListChatsUseCase(uow=uow)


def get_list_messages_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListMessagesUseCase:
    return ListMessagesUseCase(uow=uow)


def get_send_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    tg_bot_service: TelegramBotAPIService = Depends(get_telegram_bot_api_service),
) -> SendMessageUseCase:
    return SendMessageUseCase(uow=uow, tg_bot_service=tg_bot_service)


def get_handle_webhook_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> HandleWebhookUseCase:
    return HandleWebhookUseCase(uow=uow)


def get_log_bot_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> LogBotMessageUseCase:
    return LogBotMessageUseCase(uow=uow)
