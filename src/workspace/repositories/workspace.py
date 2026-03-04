from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.core.database.repositories import SoftDeleteRepository
from src.workspace.models import Workspace, WorkspaceMember

logger = get_logger(__name__)


class WorkspaceRepository(SoftDeleteRepository[Workspace]):
    model = Workspace

    async def get_paginated_by_user_id(
        self,
        session: AsyncSession,
        user_id: UUID,
        page: int = 1,
        size: int = 50,
        eager: list[Any] | None = None,
        **filters: Any,
    ) -> tuple[list[Workspace], int]:
        if page < 1:
            raise ValueError("page must be greater than or equal to 1")
        if size < 1:
            raise ValueError("size must be greater than or equal to 1")

        query = (
            select(self.model)
            .join(WorkspaceMember, self.model.id == WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_deleted.is_(False),
                self.model.is_deleted.is_(False),
            )
        )

        if filters:
            query = query.filter_by(**filters)

        if eager:
            query = query.options(*eager)

        order_by = getattr(self.model, "created_at", None)
        if order_by is None:
            order_by = getattr(self.model, "id", None)
        if order_by is not None:
            query = query.order_by(order_by.desc())

        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        result = await session.execute(query)
        items = list(result.unique().scalars().all())

        count_query = (
            select(func.count())
            .select_from(self.model)
            .join(WorkspaceMember, self.model.id == WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_deleted.is_(False),
                self.model.is_deleted.is_(False),
            )
        )

        if filters:
            count_query = count_query.filter_by(**filters)

        total_result = await session.execute(count_query)
        total = int(total_result.scalar_one())

        return items, total
