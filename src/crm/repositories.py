from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.core.database.repositories import SoftDeleteRepository
from src.crm.models import TelegramUser

logger = get_logger(__name__)


class TelegramUserRepository(SoftDeleteRepository[TelegramUser]):
    model = TelegramUser

    async def upsert(
        self, session: AsyncSession, bot_id: UUID, tg_data: dict[str, Any]
    ) -> TelegramUser:
        """
        Creates or updates a TelegramUser.
        Since we have a unique constraint (tg_user_id, bot_id), we use upsert.
        """
        stmt = (
            insert(self.model)
            .values(
                bot_id=bot_id,
                tg_user_id=tg_data["id"],
                first_name=tg_data.get("first_name"),
                username=tg_data.get("username"),
                language_code=tg_data.get("language_code"),
            )
            .on_conflict_do_update(
                index_elements=["tg_user_id", "bot_id"],
                set_={
                    "first_name": tg_data.get("first_name"),
                    "username": tg_data.get("username"),
                    "language_code": tg_data.get("language_code"),
                    "updated_at": func.now(),
                    "deleted_at": None,
                    "is_deleted": False,
                },
            )
            .returning(self.model)
        )

        result = await session.execute(stmt)
        return result.scalar_one()

    async def get_targeted_users(
        self, session: AsyncSession, bot_id: UUID, cutoff_date: Any | None = None
    ) -> list[TelegramUser]:
        """
        Retrieves all active Telegram users for a specific bot,
        optionally filtering by those updated after a cutoff date.
        """
        query = select(self.model).where(
            self.model.bot_id == bot_id,
            self.model.is_deleted.is_(False),
        )
        if cutoff_date is not None:
            query = query.where(self.model.updated_at >= cutoff_date)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def count_by_bot(self, session: AsyncSession, bot_id: UUID) -> int:
        """Total non-deleted TelegramUsers for a bot."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.bot_id == bot_id, self.model.is_deleted.is_(False))
        )
        return int((await session.execute(stmt)).scalar_one())
