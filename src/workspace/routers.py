from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.workspace.schemas import WorkspaceCreateRequest, WorkspaceViewModel
from src.workspace.usecases.create_workspace import (
    CreateWorkspaceUseCase,
    get_create_workspace_use_case,
)
from src.user.auth.dependencies import get_current_user
from src.user.auth.permissions.checker import require_permission
from src.workspace.permissions.enum import WorkspacePermission
from src.user.models import User

router = APIRouter()


@router.post(
    "/",
    response_model=WorkspaceViewModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    workspace_data: WorkspaceCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[CreateWorkspaceUseCase, Depends(get_create_workspace_use_case)],
) -> WorkspaceViewModel:
    """
    Creates a new workspace.
    """
    return await use_case.execute(
        user_id=current_user.id,
        data=workspace_data,
    )
