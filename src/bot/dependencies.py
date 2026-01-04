from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.enums import BotRole
from src.bot.models import Bot
from src.bot.repositories.admin_bot_role import AdminBotRoleRepository
from src.core.database.session import get_session
from src.core.errors.exceptions import (
    AccessForbiddenException,
    InstanceNotFoundException,
)
from src.user.auth.dependencies import get_current_user
from src.user.enums import SystemRole
from src.user.models import User


async def get_current_bot_role(
    bot_id: Annotated[UUID, Path(...)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BotRole:
    """
    Determines the effective role of the current user in the context of the specified bot.
    Implements the hierarchy: System Owner > Explicit Bot Role.
    """

    bot = await session.get(Bot, bot_id)
    if not bot:
        raise InstanceNotFoundException("Bot not found")

    is_system_owner = (
        user.role == SystemRole.OWNER and user.workspace_id == bot.workspace_id
    )

    if is_system_owner:
        return BotRole.ADMIN

    role = await AdminBotRoleRepository().get_role(
        session, admin_id=user.id, bot_id=bot_id
    )

    if not role:
        raise AccessForbiddenException("You do not have access to this bot")

    return role
