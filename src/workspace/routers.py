from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_session
from src.core.pagination import PaginatedResponse, PaginationParams
from src.user.auth.dependencies import get_current_user
from src.user.models import User
from src.workspace.dependencies import (
    get_workspace_member_service,
    get_workspace_service,
)
from src.workspace.models import WorkspaceMember
from src.workspace.permissions.checker import require_workspace_permission
from src.workspace.permissions.enum import WorkspacePermission
from src.workspace.schemas import (
    InviteMemberRequest,
    InviteSuccessResponse,
    WorkspaceCreateRequest,
    WorkspaceMemberViewModel,
    WorkspaceViewModel,
)
from src.workspace.services.workspace import WorkspaceService
from src.workspace.services.workspace_member import WorkspaceMemberService
from src.workspace.usecases.create_workspace import (
    CreateWorkspaceUseCase,
    get_create_workspace_use_case,
)
from src.workspace.usecases.invite_member import (
    InviteMemberUseCase,
    get_invite_member_use_case,
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
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaginatedResponse[WorkspaceViewModel]:
    """
    Returns a list of workspaces.
    """
    return await workspace_service.get_paginated_by_user_id(
        user_id=current_user.id,
        session=session,
        pagination=pagination,
    )


@router.post(
    "/invite",
    status_code=status.HTTP_200_OK,
)
async def invite_member(
    data: InviteMemberRequest,
    current_member: Annotated[
        WorkspaceMember,
        Depends(require_workspace_permission(WorkspacePermission.INVITE_MEMBER)),
    ],
    use_case: Annotated[InviteMemberUseCase, Depends(get_invite_member_use_case)],
) -> InviteSuccessResponse:
    """
    Invite an existing user to the current workspace by email.
    Requires the ``INVITE_MEMBER`` permission (OWNER only by default).
    """
    return await use_case.execute(
        workspace_id=current_member.workspace_id,
        data=data,
    )


@router.get(
    "/members",
    status_code=status.HTTP_200_OK,
)
async def list_members(
    pagination: Annotated[PaginationParams, Depends()],
    current_member: Annotated[
        WorkspaceMember,
        Depends(require_workspace_permission(WorkspacePermission.VIEW_MEMBERS)),
    ],
    workspace_member_service: Annotated[
        WorkspaceMemberService, Depends(get_workspace_member_service)
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaginatedResponse[WorkspaceMemberViewModel]:
    """
    List all members of the current workspace.
    Requires the ``VIEW_MEMBERS`` permission (OWNER and MEMBER).
    """
    return await workspace_member_service.get_paginated_list(
        workspace_id=current_member.workspace_id,
        pagination=pagination,
        session=session,
    )
