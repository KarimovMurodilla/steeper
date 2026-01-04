from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from src.core.errors.exceptions import (
    AccessForbiddenException,
    PermissionDeniedException,
)
from src.user.auth.dependencies import get_current_user
from src.user.auth.permissions.enum import PlatformPermission
from src.user.models import User


def require_permission(
    required_permission: PlatformPermission,
) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """
    Global Permission Checker.
    
    Scope:
    - Checks User status (active/verified).
    - Checks Platform-level permissions (Superuser actions).
    - Checks Self-management permissions (Profile).
    
    Do NOT use this for Workspace or Bot actions.
    """
    def checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not current_user.is_active:
            raise AccessForbiddenException(
                "You do not have permission to access this resource. User is blocked",
            )

        if not current_user.is_verified:
            raise AccessForbiddenException(
                "You do not have permission to access this resource. Verified users only",
            )

        if current_user.is_superuser:
            return current_user

        raise PermissionDeniedException("Global Permission denied. Superuser privileges required.")

    return checker
