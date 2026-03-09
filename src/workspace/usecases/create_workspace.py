from uuid import UUID

from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork
from src.workspace.enums import WorkspaceRole
from src.workspace.schemas import WorkspaceCreateRequest, WorkspaceViewModel


class CreateWorkspaceUseCase:
    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, data: WorkspaceCreateRequest
    ) -> WorkspaceViewModel:
        """
        Executes the business logic for creating a new workspace.

        Args:
            user_id (UUID): The typical unique ID of the user.
            data (WorkspaceCreateRequest): The request payload containing workspace creation data.

        Returns:
            WorkspaceViewModel: The details of the newly created workspace.
        """
        async with self.uow as uow:
            workspace = await uow.workspaces.create(uow.session, {"name": data.name})

            await uow.session.flush()

            await uow.workspace_members.create(
                uow.session,
                {
                    "user_id": user_id,
                    "workspace_id": workspace.id,
                    "role": WorkspaceRole.OWNER,
                },
            )

            await uow.commit()
            return WorkspaceViewModel.model_validate(workspace)
