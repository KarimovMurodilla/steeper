from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.dependencies import (
    get_assign_bot_admin_use_case,
    get_bot_service,
    get_create_bot_use_case,
    get_delete_bot_use_case,
    get_update_bot_use_case,
)
from src.bot.enums import BotRole
from src.bot.permissions.checker import require_bot_permission
from src.bot.permissions.enum import BotPermission
from src.bot.schemas import (
    AdminBotRoleAssignRequest,
    AdminBotRoleViewModel,
    BotCreateRequest,
    BotUpdateRequest,
    BotViewModel,
)
from src.bot.services.bot import BotService
from src.bot.usecases.assign_bot_admin import AssignBotAdminUseCase
from src.bot.usecases.create_bot import CreateBotUseCase
from src.bot.usecases.delete_bot import DeleteBotUseCase
from src.bot.usecases.update_bot import UpdateBotUseCase
from src.core.database.session import get_session
from src.core.pagination import PaginatedResponse, PaginationParams
from src.user.auth.dependencies import get_current_user
from src.user.models import User
from src.workspace.dependencies import get_current_workspace_id
from src.workspace.models import WorkspaceMember
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
    _: Annotated[
        WorkspaceMember,
        Depends(require_workspace_permission(WorkspacePermission.CREATE_BOT)),
    ],
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
    bot_service: Annotated[BotService, Depends(get_bot_service)],
    _: Annotated[
        WorkspaceMember,
        Depends(require_workspace_permission(WorkspacePermission.VIEW_DASHBOARD)),
    ],
) -> PaginatedResponse[BotViewModel]:
    """
    Gets all bots in the current user's workspace.
    Requires VIEW_DASHBOARD permission.
    """
    return await bot_service.get_paginated_list(
        session=session, pagination=pagination, workspace_id=workspace_id
    )


@router.post(
    "/{bot_id}/admins",
    response_model=AdminBotRoleViewModel,
    status_code=status.HTTP_201_CREATED,
)
async def assign_bot_admin(
    bot_id: UUID,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    data: AdminBotRoleAssignRequest,
    use_case: Annotated[AssignBotAdminUseCase, Depends(get_assign_bot_admin_use_case)],
    _: Annotated[
        BotRole,
        Depends(require_bot_permission(BotPermission.MANAGE_ROLES)),
    ],
) -> AdminBotRoleViewModel:
    """
    Assign a bot-level admin role to a user.
    Requires MANAGE_ROLES bot permission (ADMIN only).
    """
    return await use_case.execute(bot_id=bot_id, workspace_id=workspace_id, data=data)


@router.patch(
    "/{bot_id}",
    response_model=BotViewModel,
    status_code=status.HTTP_200_OK,
)
async def update_bot(
    bot_id: UUID,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    data: BotUpdateRequest,
    use_case: Annotated[UpdateBotUseCase, Depends(get_update_bot_use_case)],
    _: Annotated[
        BotRole,
        Depends(require_bot_permission(BotPermission.EDIT_SETTINGS)),
    ],
) -> BotViewModel:
    """
    Update a bot's settings.
    Requires EDIT_SETTINGS bot permission.
    """
    return await use_case.execute(bot_id=bot_id, workspace_id=workspace_id, data=data)


@router.delete(
    "/{bot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_bot(
    bot_id: UUID,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    use_case: Annotated[DeleteBotUseCase, Depends(get_delete_bot_use_case)],
    _: Annotated[
        WorkspaceMember,
        Depends(require_workspace_permission(WorkspacePermission.DELETE_BOT)),
    ],
) -> None:
    """
    Delete a bot from the workspace.
    Requires DELETE_BOT workspace permission.
    """
    await use_case.execute(bot_id=bot_id, workspace_id=workspace_id)
