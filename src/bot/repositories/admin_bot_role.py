from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.bot.enums import BotRole
from src.bot.models import AdminBotRole
from src.core.database.repositories import BaseRepository

logger = get_logger(__name__)


class AdminBotRoleRepository(BaseRepository[AdminBotRole]):
    model = AdminBotRole

    async def get_role(
        self, session: AsyncSession, admin_id: UUID, bot_id: UUID
    ) -> Optional[BotRole]:
        """Fetch the explicit role of an admin in a specific bot."""
        stmt = select(self.model.role).where(
            self.model.admin_id == admin_id, self.model.bot_id == bot_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
