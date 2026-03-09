from typing import Any

from faststream.rabbit import RabbitQueue

from loggers import get_logger
from src.realtime.broker import broker, steeper_exchange
from src.realtime.dependencies import get_connection_manager

logger = get_logger(__name__)

# Dynamic queue — each WS gateway instance gets its own exclusive queue
events_queue = RabbitQueue(
    name="",
    routing_key="workspace.*.bot.*.#",
    exclusive=True,
    auto_delete=True,
)


@broker.subscriber(  # type: ignore[untyped-decorator]
    queue=events_queue,
    exchange=steeper_exchange,
)
async def handle_realtime_event(body: dict[str, Any]) -> None:
    """
    FastStream subscriber that listens for all chat-related events.
    Broadcasts the event to clients subscribed to the specific chat OR the entire bot.
    """
    chat_id = body.get("chat_id")
    bot_id = body.get("bot_id")

    if not chat_id and not bot_id:
        logger.warning("Received event without chat_id or bot_id, skipping: %s", body)
        return

    manager = get_connection_manager()

    # Broadcast to both targets.
    # Manager will ensure no duplicates are sent using a Set union.
    await manager.broadcast(
        chat_id=str(chat_id) if chat_id else None,
        bot_id=str(bot_id) if bot_id else None,
        message=body,
    )

    logger.debug("Broadcasted event to chat %s and bot %s", chat_id, bot_id)
