from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from src.core.errors.exceptions import PermissionDeniedException
from src.workspace.permissions.enum import WorkspacePermission
from src.workspace.permissions.role_matrix import WORKSPACE_ROLE_PERMISSIONS 
from src.workspace.dependencies import get_current_workspace_member
from src.workspace.models import WorkspaceMember


def require_workspace_permission(
    required_permission: WorkspacePermission,
) -> Callable[[Annotated[WorkspaceMember, Depends(get_current_workspace_member)]], WorkspaceMember]:
    """
    Checks if the user has the required permission WITHIN the current workspace context.
    """

    def checker(
        member: Annotated[WorkspaceMember, Depends(get_current_workspace_member)],
    ) -> WorkspaceMember:
        allowed_permissions = WORKSPACE_ROLE_PERMISSIONS.get(member.role, set())

        if required_permission not in allowed_permissions:
            raise PermissionDeniedException(
                f"Workspace permission denied: {required_permission.value}"
            )

        return member

    return checker
