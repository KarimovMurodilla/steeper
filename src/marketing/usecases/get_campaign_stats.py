from uuid import UUID

from loggers import get_logger
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import InstanceNotFoundException
from src.marketing.enums import DeliveryStatus
from src.marketing.schemas import BroadcastStatsResponse

logger = get_logger(__name__)


class GetBroadcastStatsUseCase:
    """Use case for retrieving broadcast delivery statistics."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(self, broadcast_id: UUID) -> BroadcastStatsResponse:
        async with self.uow as uow:
            broadcast = await uow.broadcasts.get_single(uow.session, id=broadcast_id)
            if not broadcast:
                raise InstanceNotFoundException(ErrorCode.BROADCAST_NOT_FOUND)

            total = await uow.broadcast_deliveries.count(
                uow.session, broadcast_id=broadcast_id
            )
            sent = await uow.broadcast_deliveries.count(
                uow.session,
                broadcast_id=broadcast_id,
                status=DeliveryStatus.SUCCESS,
            )
            failed = await uow.broadcast_deliveries.count(
                uow.session,
                broadcast_id=broadcast_id,
                status=DeliveryStatus.FAILED,
            )

            return BroadcastStatsResponse(total=total, sent=sent, failed=failed)
