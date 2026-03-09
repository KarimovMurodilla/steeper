"""Chat subdomain router — mounted at /v1/bots so bot_id is in the path."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.bot.enums import BotRole
from src.bot.permissions.checker import require_bot_permission
from src.bot.permissions.enum import BotPermission
from src.communication.chat.usecases.list_chats import ListChatsUseCase
from src.communication.chat.usecases.list_messages import ListMessagesUseCase
from src.communication.chat.usecases.send_message import SendMessageUseCase
from src.communication.dependencies import (
    get_list_chats_use_case,
    get_list_messages_use_case,
    get_send_message_use_case,
)
from src.communication.schemas import (
    ChatListItemViewModel,
    CursorPaginatedResponse,
    MessageListItemViewModel,
    SendMessageRequest,
    SendMessageResponse,
)
from src.core.pagination import PaginatedResponse, PaginationParams

router = APIRouter()


@router.get(
    "/{bot_id}/chats",
    response_model=PaginatedResponse[ChatListItemViewModel],
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Permission denied"},
        404: {"description": "Bot not found"},
    },
)
async def list_bot_chats(
    bot_id: UUID,
    pagination: Annotated[PaginationParams, Depends()],
    use_case: Annotated[ListChatsUseCase, Depends(get_list_chats_use_case)],
    _: Annotated[
        BotRole,
        Depends(require_bot_permission(BotPermission.VIEW_CHATS)),
    ],
) -> PaginatedResponse[ChatListItemViewModel]:
    """
    List all chats for a bot with last message preview.
    Requires VIEW_CHATS bot permission.
    """
    return await use_case.execute(bot_id=bot_id, pagination=pagination)


@router.get(
    "/{bot_id}/chats/{chat_id}/messages",
    response_model=CursorPaginatedResponse[MessageListItemViewModel],
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Permission denied"},
        404: {"description": "Bot or Chat not found"},
    },
)
async def list_messages(
    bot_id: UUID,
    chat_id: UUID,
    use_case: Annotated[ListMessagesUseCase, Depends(get_list_messages_use_case)],
    _: Annotated[
        BotRole,
        Depends(require_bot_permission(BotPermission.VIEW_CHATS)),
    ],
    limit: int = Query(default=50, ge=1, le=100),
    cursor: UUID | None = Query(default=None),
) -> CursorPaginatedResponse[MessageListItemViewModel]:
    """
    Cursor-paginated message history for a chat.
    Requires VIEW_CHATS bot permission.
    """
    return await use_case.execute(chat_id=chat_id, limit=limit, cursor=cursor)


@router.post(
    "/{bot_id}/chats/{chat_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid payload format"},
        403: {"description": "Permission denied"},
        404: {"description": "Bot or Chat not found"},
    },
)
async def send_message(
    bot_id: UUID,
    chat_id: UUID,
    data: SendMessageRequest,
    use_case: Annotated[SendMessageUseCase, Depends(get_send_message_use_case)],
    _: Annotated[
        BotRole,
        Depends(require_bot_permission(BotPermission.SEND_MESSAGES)),
    ],
) -> SendMessageResponse:
    """
    Send a text message to the Telegram user through the bot.
    Requires SEND_MESSAGES bot permission.
    """
    return await use_case.execute(chat_id=chat_id, data=data)
