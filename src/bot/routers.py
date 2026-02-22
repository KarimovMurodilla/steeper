from src.core.pagination import PaginatedResponse
from src.core.pagination import PaginationParams
from src.core.database.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from src.bot.services.bot import BotService
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.bot.schemas import BotCreateRequest, BotViewModel
from src.bot.usecases.create_bot import (
    CreateBotUseCase,
    get_create_bot_use_case,
)
from src.bot.dependencies import get_bot_service
from src.user.auth.dependencies import get_current_user
from src.user.models import User
from src.workspace.dependencies import get_current_workspace_id
from src.workspace.permissions.checker import require_workspace_permission
from src.workspace.permissions.enum import WorkspacePermission

router = APIRouter()


@router.post(
    "/",
    response_model=BotViewModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_bot(
    bot_data: BotCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    use_case: Annotated[CreateBotUseCase, Depends(get_create_bot_use_case)],
    _=Depends(require_workspace_permission(WorkspacePermission.CREATE_BOT)),
) -> BotViewModel:
    """
    Creates a new bot in the current user's workspace.
    Requires CREATE_BOT permission.
    """
    return await use_case.execute(
        data=bot_data,
        user_id=current_user.id,
        workspace_id=workspace_id,
    )


@router.get(
    "/",
    response_model=PaginatedResponse[BotViewModel],
    status_code=status.HTTP_200_OK,
)
async def get_bots(
    current_user: Annotated[User, Depends(get_current_user)],
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    pagination: Annotated[PaginationParams, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[BotService, Depends(get_bot_service)],
    _=Depends(require_workspace_permission(WorkspacePermission.VIEW_DASHBOARD)),
) -> PaginatedResponse[BotViewModel]:
    """
    Gets all bots in the current user's workspace.
    Requires VIEW_DASHBOARD permission.
    """
    return await service.get_paginated_list(
        session=session,
        pagination=pagination,
        workspace_id=workspace_id
    )
