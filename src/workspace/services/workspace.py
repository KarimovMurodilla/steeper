from src.core.services import BaseService
from src.workspace.models import Workspace
from src.workspace.repositories.workspace import WorkspaceRepository
from src.workspace.schemas import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceViewModel,
)


class WorkspaceService(
    BaseService[
        Workspace,
        WorkspaceCreateRequest,
        WorkspaceUpdateRequest,
        WorkspaceRepository,
        WorkspaceViewModel,
    ]
):
    def __init__(
        self,
        repository: WorkspaceRepository,
    ):
        super().__init__(repository, response_schema=WorkspaceViewModel)
