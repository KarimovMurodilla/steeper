from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.core.database.repositories import SoftDeleteRepository
from src.crm.models import TelegramUser

logger = get_logger(__name__)


class TelegramUserRepository(SoftDeleteRepository[TelegramUser]):
    model = TelegramUser

    async def upsert(
        self, session: AsyncSession, bot_id: UUID, tg_data: dict
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
