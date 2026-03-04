from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from loggers import get_logger
from src.communication.models import Chat, Message
from src.core.database.repositories import SoftDeleteRepository

logger = get_logger(__name__)


class ChatRepository(SoftDeleteRepository[Chat]):
    model = Chat

    async def get_by_tg_user(
        self, session: AsyncSession, bot_id: UUID, tg_user_internal_id: UUID
    ) -> Chat | None:
        """Finds a chat by internal User ID and Bot ID."""
        stmt = select(self.model).where(
            self.model.bot_id == bot_id,
            self.model.telegram_user_id == tg_user_internal_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_paginated_by_bot(
        self,
        session: AsyncSession,
        bot_id: UUID,
        page: int,
        size: int,
    ) -> tuple[list[Chat], int]:
        """
        Fetch chats for a bot, ordered by most-recent activity,
        eagerly loading the telegram_user relationship.
        """
        base = (
            select(self.model)
            .where(
                self.model.bot_id == bot_id,
                self.model.is_deleted == False,  # noqa: E712
            )
            .options(selectinload(self.model.telegram_user))
            .order_by(self.model.updated_at.desc())
        )

        items_result = await session.execute(base.offset((page - 1) * size).limit(size))
        items = list(items_result.unique().scalars().all())

        count_q = (
            select(func.count())
            .select_from(self.model)
            .where(
                self.model.bot_id == bot_id,
                self.model.is_deleted == False,  # noqa: E712
            )
        )
        total = int((await session.execute(count_q)).scalar_one())

        return items, total

    async def get_last_message_content(
        self, session: AsyncSession, chat_id: UUID
    ) -> str | None:
        """Return the content of the most recent message in a chat."""
        stmt = (
            select(Message.content)
            .where(Message.chat_id == chat_id)
            .order_by(Message.id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
