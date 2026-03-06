import asyncio
from datetime import timedelta
from uuid import UUID

import sentry_sdk

from loggers import get_logger
from src.bot.services.telegram_api import TelegramAPIService
from src.communication.enums import ChatStatus, MessageType, SenderType
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.utils.datetime_utils import get_utc_now
from src.core.utils.encryption import decrypt_token
from src.marketing.enums import BroadcastStatus, DeliveryStatus

logger = get_logger(__name__)

RATE_LIMIT_DELAY = 0.05
DB_COMMIT_BATCH_SIZE = 50
MAX_RETRIES = 3


class ProcessBroadcastUseCase:
    """Use case for processing a broadcast campaign and dispatching messages."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        tg_service: TelegramAPIService,
    ) -> None:
        self.uow = uow
        self.tg_service = tg_service

    async def execute(self, broadcast_id: UUID) -> str:
        async with self.uow as uow:
            broadcast = await uow.broadcasts.get_single(uow.session, id=broadcast_id)
            if not broadcast:
                logger.error("Broadcast %s not found", broadcast_id)
                return f"Broadcast {broadcast_id} not found"

            bot = await uow.bots.get_single(uow.session, id=broadcast.bot_id)
            if not bot:
                logger.error(
                    "Bot %s not found for broadcast %s", broadcast.bot_id, broadcast_id
                )
                broadcast.status = BroadcastStatus.FAILED
                await uow.commit()
                return f"Bot not found for broadcast {broadcast_id}"

            token = decrypt_token(bot.token_encrypted)

            # Apply filters via repository logic
            filters = broadcast.filters or {}
            last_active_days = filters.get("last_active_days")
            cutoff_date = None
            if last_active_days is not None:
                cutoff_date = get_utc_now() - timedelta(days=int(last_active_days))

            users = await uow.telegram_users.get_targeted_users(
                uow.session, bot_id=broadcast.bot_id, cutoff_date=cutoff_date
            )

            if not users:
                logger.info("No target users found for broadcast %s", broadcast_id)
                broadcast.status = BroadcastStatus.SENT
                await uow.commit()
                return f"Broadcast {broadcast_id}: 0 users targeted"

            sent_count = 0
            failed_count = 0
            total_users = len(users)

            for index, user in enumerate(users):
                success = False
                tg_message_id = None

                for attempt in range(MAX_RETRIES):
                    try:
                        response = await self.tg_service.send_message(
                            token=token,
                            chat_id=user.tg_user_id,
                            text=broadcast.message_content,
                        )
                        success = bool(response)
                        if success and isinstance(response, dict):
                            tg_message_id = response.get("message_id")
                        break

                    except Exception as e:
                        error_msg = str(e).lower()
                        if "429" in error_msg or "too many requests" in error_msg:
                            sleep_time = 3 * (attempt + 1)
                            logger.warning(
                                "Rate limit hit for user %s (Attempt %s/%s). Sleeping for %ss...",
                                user.tg_user_id,
                                attempt + 1,
                                MAX_RETRIES,
                                sleep_time,
                            )
                            await asyncio.sleep(sleep_time)
                        else:
                            logger.warning(
                                "Failed to send broadcast to user %s: %s",
                                user.tg_user_id,
                                e,
                            )
                            break

                status = DeliveryStatus.SUCCESS if success else DeliveryStatus.FAILED

                await uow.broadcast_deliveries.create(
                    uow.session,
                    {
                        "broadcast_id": broadcast_id,
                        "telegram_user_id": user.id,
                        "status": status,
                    },
                )

                if success and tg_message_id:
                    chat = await uow.chats.get_by_tg_user(
                        uow.session, broadcast.bot_id, user.id
                    )
                    if not chat:
                        chat = await uow.chats.create(
                            uow.session,
                            {
                                "bot_id": broadcast.bot_id,
                                "telegram_user_id": user.id,
                                "status": ChatStatus.OPEN,
                            },
                        )
                        await uow.session.flush()

                    await uow.messages.create(
                        uow.session,
                        {
                            "chat_id": chat.id,
                            "sender_type": SenderType.BOT,
                            "message_type": MessageType.TEXT,
                            "tg_message_id": tg_message_id,
                            "content": broadcast.message_content,
                            "metadata_info": {"broadcast_id": str(broadcast_id)},
                        },
                    )

                if status == DeliveryStatus.SUCCESS:
                    sent_count += 1
                else:
                    failed_count += 1

                if (index + 1) % DB_COMMIT_BATCH_SIZE == 0:
                    try:
                        await uow.commit()
                    except Exception as e:
                        logger.exception(
                            "Failed to batch commit at index %s: %s", index, e
                        )

                await asyncio.sleep(RATE_LIMIT_DELAY)

            broadcast = await uow.broadcasts.get_single(uow.session, id=broadcast_id)
            if broadcast:
                broadcast.status = (
                    BroadcastStatus.SENT if sent_count > 0 else BroadcastStatus.FAILED
                )

            try:
                await uow.commit()
            except Exception as e:
                logger.exception(
                    "Failed to commit final broadcast %s results: %s", broadcast_id, e
                )
                sentry_sdk.capture_exception(e)
                return f"Broadcast {broadcast_id} results commit failed"

            summary = (
                f"Broadcast {broadcast_id}: "
                f"sent={sent_count}, failed={failed_count}, total={total_users}"
            )
            logger.info(summary)
            return summary
