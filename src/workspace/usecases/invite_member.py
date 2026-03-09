"""Use case: invite a user to a workspace by telegram_id."""

from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
)
from src.workspace.schemas import (
    InviteMemberRequest,
    InviteSuccessResponse,
)

logger = get_logger(__name__)


class InviteMemberUseCase:
    """
    Invites an existing user to a workspace by telegram_id.

    Steps:
      1. Look up the user by telegram_id.
      2. Guard against duplicate membership.
      3. Persist the new WorkspaceMember record.
      4. (Optional) Send a workspace-invite telegram notification.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(
        self,
        workspace_id: UUID,
        data: InviteMemberRequest,
    ) -> InviteSuccessResponse:
        async with self.uow as uow:
            # 1. Resolve user by telegram_id
            user = await uow.users.get_single(uow.session, telegram_id=data.telegram_id)
            if not user:
                raise InstanceNotFoundException(ErrorCode.USER_NOT_FOUND)

            # 2. Guard against duplicate membership
            already_member = await uow.workspace_members.exists(
                uow.session,
                user_id=user.id,
                workspace_id=workspace_id,
            )
            if already_member:
                raise InstanceAlreadyExistsException(ErrorCode.WORKSPACE_ALREADY_MEMBER)

            # 3. Persist membership
            # workspace = await uow.workspaces.get_single(uow.session, id=workspace_id)

            await uow.workspace_members.create(
                uow.session,
                {
                    "user_id": user.id,
                    "workspace_id": workspace_id,
                    "role": data.role,
                },
            )
            await uow.commit()

        # TODO: Send invite telegram notification (outside transaction — fire-and-log)
        logger.info("User %s invited to workspace %s", data.telegram_id, workspace_id)

        return InviteSuccessResponse(success=True)


def get_invite_member_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> InviteMemberUseCase:
    return InviteMemberUseCase(uow=uow)
