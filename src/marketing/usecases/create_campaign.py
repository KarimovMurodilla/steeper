from typing import cast
from uuid import UUID

from celery_tasks.types import CeleryTask
from loggers import get_logger
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.marketing.enums import BroadcastStatus
from src.marketing.schemas import BroadcastCreateRequest, BroadcastResponse
from src.marketing.tasks import process_broadcast_task

logger = get_logger(__name__)


class CreateBroadcastUseCase:
    """Use case for creating a new broadcast campaign."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, data: BroadcastCreateRequest
    ) -> BroadcastResponse:
        async with self.uow as uow:
            bot = await uow.bots.get_single(uow.session, id=data.bot_id)
            if not bot:
                raise InstanceNotFoundException("Bot not found")

            status = (
                BroadcastStatus.SCHEDULED if data.schedule_at else BroadcastStatus.DRAFT
            )

            broadcast = await uow.broadcasts.create(
                uow.session,
                {
                    "bot_id": data.bot_id,
                    "created_by": user_id,
                    "message_content": data.text,
                    "filters": data.filters.model_dump() if data.filters else {},
                    "status": status,
                    "scheduled_at": data.schedule_at,
                },
            )

            await uow.commit()

            if data.schedule_at:
                task = cast(CeleryTask, process_broadcast_task)
                task.apply_async(args=[str(broadcast.id)], eta=data.schedule_at)
                logger.info(
                    "Broadcast %s scheduled for %s", broadcast.id, data.schedule_at
                )

            return BroadcastResponse.model_validate(broadcast)
