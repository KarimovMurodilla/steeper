from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_session
from src.user.auth.dependencies import (
    get_current_user,
)
from src.user.auth.permissions.checker import require_permission
from src.user.auth.routers import router as auth_router
from src.user.dependencies import get_user_service
from src.user.models import User
from src.user.schemas import (
    UserProfileViewModel,
    UserSummaryViewModel,
)
from src.user.services import UserService
from src.workspace.permissions.enum import WorkspacePermission

router = APIRouter()

router.include_router(auth_router, prefix="/auth")


@router.get(
    "/me",
    response_model=UserProfileViewModel,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserProfileViewModel:
    """
    Returns the current user's information.
    """
    return UserProfileViewModel.model_validate(current_user)


@router.get(
    "/{user_id}",
    response_model=UserSummaryViewModel,
    responses={
        403: {"description": "Permission denied"},
        404: {"description": "User not found"},
    },
)
async def get_user_info_by_id(
    user_id: UUID,
    current_user: Annotated[
        User, Depends(require_permission(WorkspacePermission.VIEW_MEMBERS))
    ],
    user_service: Annotated[UserService, Depends(get_user_service)],
    session: AsyncSession = Depends(get_session),
) -> UserSummaryViewModel:
    """
    Returns the user's information by ID.
    """
    user = await user_service.get_single(session, id=user_id)
    return UserSummaryViewModel.model_validate(user)
