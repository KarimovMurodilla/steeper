from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Load

from src.core.pagination import PaginatedResponse, PaginationParams
from src.core.schemas import Base
from src.core.services import BaseService
from src.workspace.models import WorkspaceMember
from src.workspace.repositories.workspace_member import WorkspaceMemberRepository
from src.workspace.schemas import WorkspaceMemberViewModel


class WorkspaceMemberService(
    BaseService[
        WorkspaceMember,
        Base,
        Base,
        WorkspaceMemberRepository,
        WorkspaceMemberViewModel,
    ]
):
    def __init__(
        self,
        repository: WorkspaceMemberRepository,
    ):
        super().__init__(repository, response_schema=WorkspaceMemberViewModel)

    async def get_paginated_list(
        self,
        session: AsyncSession,
        pagination: PaginationParams,
        eager: list[Load] | None = None,
        **filters: Any,
    ) -> PaginatedResponse[WorkspaceMemberViewModel]:
        return await super().get_paginated_list(
            session=session,
            pagination=pagination,
            eager=eager,
            **filters,
        )
