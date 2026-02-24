from src.core.database.session import get_unit_of_work
from fastapi import Depends
from uuid import UUID

from sqlalchemy.orm import selectinload

from src.core.pagination import PaginatedResponse, PaginationParams, make_paginated_response
from src.workspace.models import WorkspaceMember
from src.workspace.repositories.workspace_member import WorkspaceMemberRepository
from src.workspace.schemas import MemberListItemViewModel
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork


class ListMembersUseCase:
    """
    Returns a paginated list of workspace members with their email and role.

    Eagerly loads the related ``User`` to avoid N+1 queries.
    """

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self,
        workspace_id: UUID,
        pagination: PaginationParams,
    ) -> PaginatedResponse[MemberListItemViewModel]:
        async with self.uow as uow:
            items, total = await uow.workspace_members.get_paginated_list(
                uow.session,
                page=pagination.page,
                size=pagination.size,
                eager=[selectinload(WorkspaceMember.user)],
                workspace_id=workspace_id,
            )

            member_views = [
                MemberListItemViewModel(
                    user_id=member.user_id,
                    email=member.user.email,
                    role=member.role,
                )
                for member in items
            ]

            return make_paginated_response(
                items=member_views,
                total=total,
                pagination=pagination,
            )


def get_list_members_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListMembersUseCase:
    return ListMembersUseCase(uow=uow)
