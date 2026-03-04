from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.communication.models import Chat, Message
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

    async def count_by_bot(self, session: AsyncSession, bot_id: UUID) -> int:
        """Total messages across all chats for a bot."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .join(Chat, Chat.id == self.model.chat_id)
            .where(Chat.bot_id == bot_id)
        )
        return int((await session.execute(stmt)).scalar_one())

    async def count_dau_by_bot(self, session: AsyncSession, bot_id: UUID) -> int:
        """
        Daily Active Users: distinct telegram users that had activity
        (at least one message in any chat for this bot) today (UTC).
        """
        today_start = date.today()
        stmt = (
            select(func.count(func.distinct(Chat.telegram_user_id)))
            .select_from(self.model)
            .join(Chat, Chat.id == self.model.chat_id)
            .where(
                Chat.bot_id == bot_id,
                func.date(self.model.created_at) == today_start,
            )
        )
        return int((await session.execute(stmt)).scalar_one())
