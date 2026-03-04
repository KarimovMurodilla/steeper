from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import (
    PaginatedResponse,
    PaginationParams,
    make_paginated_response,
)
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

    async def get_paginated_by_user_id(
        self,
        session: AsyncSession,
        user_id: UUID,
        pagination: PaginationParams,
        **filters: Any,
    ) -> PaginatedResponse[WorkspaceViewModel]:
        items, total = await self.repository.get_paginated_by_user_id(
            session=session,
            user_id=user_id,
            page=pagination.page,
            size=pagination.size,
            **filters,
        )

        return make_paginated_response(
            items=items,
            total=total,
            pagination=pagination,
            schema=WorkspaceViewModel,
        )
