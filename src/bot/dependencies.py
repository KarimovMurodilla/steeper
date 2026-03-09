from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.enums import BotRole
from src.bot.models import Bot
from src.bot.repositories.admin_bot_role import AdminBotRoleRepository
from src.bot.repositories.bot import BotRepository
from src.bot.services.bot import BotService
from src.bot.usecases.assign_bot_admin import AssignBotAdminUseCase
from src.bot.usecases.create_bot import CreateBotUseCase
from src.bot.usecases.delete_bot import DeleteBotUseCase
from src.bot.usecases.update_bot import UpdateBotUseCase
from src.core.database.session import get_session, get_unit_of_work
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import (
    AccessForbiddenException,
    InstanceNotFoundException,
)
from src.integrations.telegram.bot.telegram_bot_api import TelegramBotAPIService
from src.integrations.telegram.dependencies import get_telegram_bot_api_service
from src.workspace.dependencies import get_current_workspace_member
from src.workspace.enums import WorkspaceRole
from src.workspace.models import WorkspaceMember


async def get_current_bot_role(
    bot_id: Annotated[UUID, Path(...)],
    member: Annotated[WorkspaceMember, Depends(get_current_workspace_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BotRole:
    """
    Determines the effective role of the current user in the context of the specified bot.
    Implements the hierarchy: System Owner > Explicit Bot Role.
    """

    bot = await session.get(Bot, bot_id)
    if not bot:
        raise InstanceNotFoundException(ErrorCode.BOT_NOT_FOUND)

    is_system_owner = (
        member.role == WorkspaceRole.OWNER and member.workspace_id == bot.workspace_id
    )

    if is_system_owner:
        return BotRole.ADMIN

    role = await AdminBotRoleRepository().get_role(
        session, admin_id=member.user_id, bot_id=bot_id
    )

    if not role:
        raise AccessForbiddenException(ErrorCode.AUTH_ACCESS_FORBIDDEN)

    return role


async def get_bot_service() -> BotService:
    """
    Dependency to get the BotService.
    """
    repo = BotRepository()
    return BotService(repository=repo)


def get_create_bot_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    tg_service: TelegramBotAPIService = Depends(get_telegram_bot_api_service),
) -> CreateBotUseCase:
    return CreateBotUseCase(uow=uow, tg_service=tg_service)


def get_assign_bot_admin_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> AssignBotAdminUseCase:
    return AssignBotAdminUseCase(uow=uow)


def get_update_bot_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    tg_service: TelegramBotAPIService = Depends(get_telegram_bot_api_service),
) -> UpdateBotUseCase:
    return UpdateBotUseCase(uow=uow, tg_service=tg_service)


def get_delete_bot_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    tg_service: TelegramBotAPIService = Depends(get_telegram_bot_api_service),
) -> DeleteBotUseCase:
    return DeleteBotUseCase(uow=uow, tg_service=tg_service)
