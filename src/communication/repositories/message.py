from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.communication.models import Message
from src.core.database.repositories import BaseRepository

logger = get_logger(__name__)


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def get_cursor_paginated(
        self,
        session: AsyncSession,
        chat_id: UUID,
        limit: int = 50,
        cursor: UUID | None = None,
    ) -> list[Message]:
        """
        Cursor-based pagination using UUID7 ordering.
        Messages are returned newest-first (DESC).
        The cursor is the `id` of the last item from the previous page.
        """
        stmt = select(self.model).where(self.model.chat_id == chat_id)

        if cursor is not None:
            stmt = stmt.where(self.model.id < cursor)

        stmt = stmt.order_by(self.model.id.desc()).limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())
