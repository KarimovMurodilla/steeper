from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_session
from src.user.auth.dependencies import get_current_user
from src.user.models import User
from src.workspace.models import WorkspaceMember
from src.workspace.repositories.workspace_member import WorkspaceMemberRepository

from src.core.errors.exceptions import PermissionDeniedException


async def get_current_workspace_id(
    x_workspace_id: Annotated[UUID, Header(alias="X-Workspace-ID", description="ID of the active workspace")],
) -> UUID:
    """
    Extracts the workspace ID from the request headers.
    Front-end must send 'X-Workspace-ID: <uuid>' with every request that requires workspace context.
    """
    return x_workspace_id


async def get_current_workspace_member(
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WorkspaceMember:
    """
    Validates that the current user is a member of the requested workspace
    and returns their membership record (which contains their specific Role).
    """

    member = await WorkspaceMemberRepository().get_single(
        session, user_id=user.id, workspace_id=workspace_id
    )

    if not member:
        raise PermissionDeniedException(
            "You are not a member of this workspace or it does not exist."
        )
    
    return member
