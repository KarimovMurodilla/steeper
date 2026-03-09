"""Use case: assign a bot admin role to a workspace member."""

from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.bot.schemas import AdminBotRoleAssignRequest, AdminBotRoleViewModel
from src.core.database.session import get_unit_of_work
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
)

logger = get_logger(__name__)


class AssignBotAdminUseCase:
    """
    Assigns a bot-level admin role to a user.

    Steps:
      1. Verify the target user exists.
      2. Verify the bot exists and belongs to the same workspace.
      3. Guard against duplicate role assignment.
      4. Persist the AdminBotRole record.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self._uow = uow

    async def execute(
        self,
        bot_id: UUID,
        workspace_id: UUID,
        data: AdminBotRoleAssignRequest,
    ) -> AdminBotRoleViewModel:
        async with self._uow as uow:
            user = await uow.users.get_single(uow.session, id=data.user_id)
            if not user:
                raise InstanceNotFoundException(ErrorCode.USER_NOT_FOUND)

            bot = await uow.bots.get_single(
                uow.session, id=bot_id, workspace_id=workspace_id
            )
            if not bot:
                raise InstanceNotFoundException(ErrorCode.BOT_NOT_FOUND)

            user_workspace = await uow.workspace_members.get_single(
                uow.session,
                user_id=data.user_id,
                workspace_id=workspace_id,
            )
            if not user_workspace:
                raise InstanceNotFoundException(ErrorCode.WORKSPACE_MEMBER_NOT_FOUND)

            existing = await uow.admin_bot_roles.exists(
                uow.session,
                admin_id=data.user_id,
                bot_id=bot_id,
            )
            if existing:
                raise InstanceAlreadyExistsException(ErrorCode.BOT_ADMIN_ALREADY_EXISTS)

            admin_role = await uow.admin_bot_roles.create(
                uow.session,
                {
                    "admin_id": data.user_id,
                    "bot_id": bot_id,
                    "role": data.role,
                },
            )
            await uow.commit()

            return AdminBotRoleViewModel.model_validate(admin_role)


def get_assign_bot_admin_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> AssignBotAdminUseCase:
    return AssignBotAdminUseCase(uow=uow)
