from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.communication.models import Chat
from src.core.database.repositories import SoftDeleteRepository

logger = get_logger(__name__)


class ChatRepository(SoftDeleteRepository[Chat]):
    model = Chat

    async def get_by_tg_user(
        self, session: AsyncSession, bot_id: UUID, tg_user_internal_id: UUID
    ) -> Optional[Chat]:
        """Finds a chat by internal User ID and Bot ID."""
        stmt = select(self.model).where(
            self.model.bot_id == bot_id,
            self.model.telegram_user_id == tg_user_internal_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
