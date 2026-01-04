from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.bot.models import Bot
from src.core.database.repositories import SoftDeleteRepository

logger = get_logger(__name__)


class BotRepository(SoftDeleteRepository[Bot]):
    model = Bot

    async def get_by_token_hash(
        self, session: AsyncSession, token_hash: str
    ) -> Optional[Bot]:
        """Find a bot by its token hash (useful for webhooks)."""
        stmt = select(self.model).where(self.model.token_hash == token_hash)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
