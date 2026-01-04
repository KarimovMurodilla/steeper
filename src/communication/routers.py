from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.communication.schemas import TelegramUpdatePayload, BotMessagePayload
from src.communication.usecases.handle_webhook import (
    HandleWebhookUseCase,
    get_handle_webhook_use_case,
)
from src.communication.usecases.log_bot_message import (
    LogBotMessageUseCase,
    get_log_bot_message_use_case,
)
from src.core.schemas import SuccessResponse

router = APIRouter()


@router.post(
    "/webhook/{token_hash}",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse,
)
async def handle_telegram_webhook(
    token_hash: str,
    payload: TelegramUpdatePayload,
    use_case: Annotated[HandleWebhookUseCase, Depends(get_handle_webhook_use_case)],
) -> SuccessResponse:
    """
    Universal entry point for Telegram Updates.
    Accepts data from:
    1. Direct Telegram Webhook (setWebhook).
    2. Custom Middleware (e.g., Aiogram) acting as a proxy.

    The payload must match the standard Telegram 'Update' JSON structure.
    """
    return await use_case.execute(token_hash, payload)


@router.post(
    "/webhook/{token_hash}/bot-message",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse,
)
async def log_bot_message(
    token_hash: str,
    payload: BotMessagePayload,
    use_case: Annotated[LogBotMessageUseCase, Depends(get_log_bot_message_use_case)],
) -> SuccessResponse:
    """
    Accepts data from:
    1. Our frontend.
    2. Custom Middleware (e.g., Aiogram) acting as a proxy.
    """
    return await use_case.execute(token_hash, payload)
