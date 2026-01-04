from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.bot.schemas import BotCreateRequest, BotViewModel
from src.bot.usecases.create_bot import (
    CreateBotUseCase,
    get_create_bot_use_case,
)
from src.user.auth.dependencies import get_current_user
from src.user.auth.permissions.checker import require_permission
from src.workspace.permissions.enum import WorkspacePermission
from src.user.models import User

router = APIRouter()


@router.post(
    "/",
    response_model=BotViewModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_bot(
    bot_data: BotCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[CreateBotUseCase, Depends(get_create_bot_use_case)],
    _=Depends(require_permission(WorkspacePermission.CREATE_BOT)),
) -> BotViewModel:
    """
    Creates a new bot in the current user's workspace.
    Requires CREATE_BOT permission.
    """
    return await use_case.execute(
        data=bot_data,
        user_id=current_user.id,
        workspace_id=current_user.workspace_id,
    )
