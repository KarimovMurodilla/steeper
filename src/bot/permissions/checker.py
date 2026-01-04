from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from src.bot.dependencies import get_current_bot_role
from src.bot.enums import BotRole
from src.bot.permissions.enum import BotPermission
from src.bot.permissions.role_matrix import BOT_ROLE_PERMISSIONS
from src.core.errors.exceptions import PermissionDeniedException


def require_bot_permission(
    required_permission: BotPermission,
) -> Callable[[Annotated[BotRole, Depends(get_current_bot_role)]], BotRole]:
    """
    Dependency factory that verifies if the current user (in the context of a specific bot)
    holds the required permission.

    Args:
        required_permission: The specific BotPermission required for the endpoint.

    Returns:
        The user's BotRole if authorized, raises PermissionDeniedException otherwise.
    """

    def checker(
        current_role: Annotated[BotRole, Depends(get_current_bot_role)],
    ) -> BotRole:
        # 1. Get the allowed permissions for the user's role from the matrix
        allowed_permissions = BOT_ROLE_PERMISSIONS.get(current_role, set())

        # 2. Verify permission
        if required_permission not in allowed_permissions:
            raise PermissionDeniedException(
                f"Missing bot permission: {required_permission.value}"
            )

        return current_role

    return checker
