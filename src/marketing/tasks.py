from src.bot.services.telegram_api import TelegramAPIService
from src.core.database.uow import get_uow
import sentry_sdk
import uuid
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from celery_tasks.main import (
    celery_app,  # noqa: F401
    local_async_session,
)
from celery_tasks.types import typed_shared_task
from loggers import get_logger
from src.core.utils.coroutine_runner import execute_coroutine_sync
from src.marketing.usecases.process_broadcast import ProcessBroadcastUseCase

logger = get_logger(__name__)


@typed_shared_task(name="process_broadcast")
def process_broadcast_task(broadcast_id: str) -> str:
    result = execute_coroutine_sync(
        coroutine=lambda: _process_broadcast(broadcast_id)
    )
    return result


async def _process_broadcast(broadcast_id: str) -> str:
    try:
        async with local_async_session() as session:
            uow = await get_uow(session)
            tg_service = TelegramAPIService()
            use_case = ProcessBroadcastUseCase(uow=uow, tg_service=tg_service)
            return await use_case.execute(broadcast_id=uuid.UUID(broadcast_id))
    except (IntegrityError, SQLAlchemyError) as e:
        logger.exception("Broadcast %s processing failed: %s", broadcast_id, e)
        sentry_sdk.capture_exception(e)
        return f"Broadcast {broadcast_id} processing failed"
    return f"Broadcast {broadcast_id} processing failed due to unhandled UoW completion"
