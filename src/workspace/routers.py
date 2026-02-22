from src.workspace.dependencies import get_workspace_member_service
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_session
from src.core.pagination import PaginatedResponse, PaginationParams
from src.user.auth.dependencies import get_current_user
from src.user.models import User
from src.workspace.dependencies import get_workspace_service
from src.workspace.schemas import WorkspaceCreateRequest, WorkspaceViewModel, WorkspaceMemberViewModel
from src.workspace.services.workspace_member import WorkspaceMemberService
from src.workspace.usecases.create_workspace import (
    CreateWorkspaceUseCase,
    get_create_workspace_use_case,
)

router = APIRouter()


@router.post(
    "/",
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


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
)
async def get_workspaces(
    pagination: Annotated[PaginationParams, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    workspace_member_service: Annotated[WorkspaceMemberService, Depends(get_workspace_member_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaginatedResponse[WorkspaceMemberViewModel]:
    """
    Returns a list of workspaces.
    """
    return await workspace_member_service.get_paginated_list(
        user_id=current_user.id,
        session=session,
        pagination=pagination,
    )
