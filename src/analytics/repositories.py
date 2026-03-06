from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.analytics.models import AuditLog
from src.core.database.repositories import BaseRepository
from src.user.models import User

logger = get_logger(__name__)


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def get_paginated_with_actor(
        self,
        session: AsyncSession,
        page: int,
        size: int,
        bot_id: UUID | None = None,
    ) -> tuple[list[tuple[AuditLog, int]], int]:
        """
        Returns paginated (AuditLog, actor_telegram_id) tuples, joined with users.
        Ordered by created_at DESC (newest first).
        Optionally filtered by bot_id.
        """
        base = (
            select(self.model, User.telegram_id)
            .join(User, User.id == self.model.admin_id)
            .order_by(self.model.created_at.desc())
        )
        if bot_id is not None:
            base = base.where(self.model.bot_id == bot_id)

        items_q = base.offset((page - 1) * size).limit(size)
        result = await session.execute(items_q)
        rows = [(row[0], row[1]) for row in result.all()]

        count_q = select(func.count()).select_from(self.model)
        if bot_id is not None:
            count_q = count_q.where(self.model.bot_id == bot_id)
        total = (await session.execute(count_q)).scalar_one()

        return rows, int(total)
