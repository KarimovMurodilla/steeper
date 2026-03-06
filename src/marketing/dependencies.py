from fastapi import Depends

from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.marketing.usecases.create_campaign import CreateBroadcastUseCase
from src.marketing.usecases.get_campaign_stats import GetBroadcastStatsUseCase
from src.marketing.usecases.launch_broadcast import LaunchBroadcastUseCase


def get_create_broadcast_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> CreateBroadcastUseCase:
    return CreateBroadcastUseCase(uow=uow)


def get_launch_broadcast_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> LaunchBroadcastUseCase:
    return LaunchBroadcastUseCase(uow=uow)


def get_get_broadcast_stats_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> GetBroadcastStatsUseCase:
    return GetBroadcastStatsUseCase(uow=uow)
