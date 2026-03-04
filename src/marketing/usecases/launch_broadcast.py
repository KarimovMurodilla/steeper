from typing import cast
from uuid import UUID

from celery_tasks.types import CeleryTask
from loggers import get_logger
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import (
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.core.schemas import SuccessResponse
from src.marketing.enums import BroadcastStatus
from src.marketing.tasks import process_broadcast_task

logger = get_logger(__name__)

_LAUNCHABLE_STATUSES = {BroadcastStatus.DRAFT, BroadcastStatus.SCHEDULED}


class LaunchBroadcastUseCase:
    """Use case for manually launching a broadcast campaign."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(self, broadcast_id: UUID) -> SuccessResponse:
        async with self.uow as uow:
            broadcast = await uow.broadcasts.get_single(
                uow.session, id=broadcast_id, for_update=True
            )
            if not broadcast:
                raise InstanceNotFoundException("Broadcast not found")

            if broadcast.status not in _LAUNCHABLE_STATUSES:
                raise InstanceProcessingException(
                    f"Broadcast cannot be launched from status '{broadcast.status}'"
                )

            broadcast.status = BroadcastStatus.PROCESSING
            await uow.commit()

        task = cast(CeleryTask, process_broadcast_task)
        task.delay(str(broadcast_id))
        logger.info("Broadcast %s dispatched for processing", broadcast_id)

        return SuccessResponse(success=True)
