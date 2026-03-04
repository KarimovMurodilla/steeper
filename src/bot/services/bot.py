from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Load, selectinload

from src.bot.models import Bot
from src.bot.repositories.bot import BotRepository
from src.bot.schemas import BotCreateRequest, BotViewModel
from src.core.pagination import (
    PaginatedResponse,
    PaginationParams,
    make_paginated_response,
)
from src.core.schemas import Base
from src.core.services import BaseService


class BotService(BaseService[Bot, BotCreateRequest, Base, BotRepository, BotViewModel]):
    def __init__(
        self,
        repository: BotRepository,
    ):
        super().__init__(repository, response_schema=BotViewModel)

    async def get_paginated_list(
        self,
        session: AsyncSession,
        pagination: PaginationParams,
        eager: list[Load] | None = None,
        **filters: Any,
    ) -> PaginatedResponse[BotViewModel]:
        """Retrieve a paginated list of records matching the filters."""
        eager = [cast(Load, selectinload(Bot.admin_roles))]
        items, total = await self.repository.get_paginated_list(
            session=session,
            page=pagination.page,
            size=pagination.size,
            eager=eager,
            **filters,
        )
        schema_to_use: type[BotViewModel] | None = self._response_schema
        if schema_to_use is None:
            raise ValueError("response_schema must be provided for paginated responses")

        return make_paginated_response(
            items=items,
            total=total,
            pagination=pagination,
            schema=schema_to_use,
        )
