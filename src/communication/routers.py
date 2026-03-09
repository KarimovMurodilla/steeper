from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from src.communication.dependencies import (
    get_handle_webhook_use_case,
    get_log_bot_message_use_case,
)
from src.communication.schemas import BotMessagePayload, TelegramUpdatePayload
from src.communication.usecases.handle_webhook import HandleWebhookUseCase
from src.communication.usecases.log_bot_message import LogBotMessageUseCase
from src.core.schemas import SuccessResponse

router = APIRouter()


@router.post(
    "/webhook/{bot_id}",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse,
    responses={
        400: {"description": "Invalid payload format"},
        403: {"description": "Invalid Telegram secret token"},
        404: {"description": "Bot not found"},
    },
)
async def handle_telegram_webhook(
    bot_id: UUID,
    payload: TelegramUpdatePayload,
    use_case: Annotated[HandleWebhookUseCase, Depends(get_handle_webhook_use_case)],
    x_telegram_bot_api_secret_token: Annotated[str, Header()] = "",
) -> SuccessResponse:
    """
    Universal entry point for Telegram Updates.
    Accepts data from:
    1. Direct Telegram Webhook (setWebhook).
    2. Custom Middleware (e.g., Aiogram) acting as a proxy.

    The payload must match the standard Telegram 'Update' JSON structure.
    """
    return await use_case.execute(bot_id, payload, x_telegram_bot_api_secret_token)


@router.post(
    "/webhook/{token_hash}/bot-message",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse,
    responses={
        400: {"description": "Invalid payload format"},
        403: {"description": "Invalid or expired token hash"},
        404: {"description": "Bot not found"},
    },
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
