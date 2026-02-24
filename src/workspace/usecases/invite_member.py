"""Use case: invite a user to a workspace by email."""
from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork
from src.core.email_service.dependencies import get_email_service
from src.workspace.schemas import WorkspaceInviteEmailBody
from src.core.email_service.service import EmailService
from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
)
from src.workspace.schemas import InviteMemberRequest, InviteSuccessResponse

logger = get_logger(__name__)


class InviteMemberUseCase:
    """
    Invites an existing user to a workspace by email.

    Steps:
      1. Look up the user by e-mail address.
      2. Guard against duplicate membership.
      3. Persist the new WorkspaceMember record.
      4. Send a workspace-invite email notification via the injected EmailService.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        email_service: EmailService,
    ) -> None:
        self.uow = uow
        self.email_service = email_service

    async def execute(
        self,
        workspace_id: UUID,
        data: InviteMemberRequest,
    ) -> InviteSuccessResponse:
        async with self.uow as uow:
            # 1. Resolve user by email
            user = await uow.users.get_single(uow.session, email=str(data.email))
            if not user:
                raise InstanceNotFoundException(
                    f"No user found with email '{data.email}'."
                )

            # 2. Guard against duplicate membership
            already_member = await uow.workspace_members.exists(
                uow.session,
                user_id=user.id,
                workspace_id=workspace_id,
            )
            if already_member:
                raise InstanceAlreadyExistsException(
                    f"User '{data.email}' is already a member of this workspace."
                )

            # 3. Persist membership
            workspace = await uow.workspaces.get_single(
                uow.session, id=workspace_id
            )

            await uow.workspace_members.create(
                uow.session,
                {
                    "user_id": user.id,
                    "workspace_id": workspace_id,
                    "role": data.role,
                },
            )
            await uow.commit()

        # 4. Send invite email (outside transaction — fire-and-log)
        try:
            workspace_name = workspace.name if workspace else str(workspace_id)
            await self.email_service.send_template_email(
                subject="You've been invited to a workspace",
                recipients=str(data.email),
                template_name="workspace_invite.html",
                template_body=WorkspaceInviteEmailBody(
                    title="Workspace Invitation",
                    name=user.full_name,
                    workspace_name=workspace_name,
                    role=data.role.value.capitalize(),
                    link="",  # TODO: replace with actual accept-invite deep-link
                ),
            )
        except Exception:
            # Email is best-effort; membership is already committed
            logger.exception(
                "Failed to send invite email to '%s', but membership was created.",
                data.email,
            )

        return InviteSuccessResponse(success=True)


def get_invite_member_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    email_service: EmailService = Depends(get_email_service),
) -> InviteMemberUseCase:
    return InviteMemberUseCase(uow=uow, email_service=email_service)
