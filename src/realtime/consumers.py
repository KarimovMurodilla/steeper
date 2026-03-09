from typing import Any

from faststream.rabbit import RabbitQueue

from loggers import get_logger
from src.realtime.broker import broker, steeper_exchange
from src.realtime.dependencies import get_connection_manager

logger = get_logger(__name__)

# Dynamic queue — each WS gateway instance gets its own exclusive queue
# so that every gateway receives every event (fan-out behaviour).
events_queue = RabbitQueue(
    name="",  # Empty name → server-generated unique queue name
    routing_key="workspace.*.bot.*.chat.*.#",
    exclusive=True,
    auto_delete=True,
)


@broker.subscriber(  # type: ignore[untyped-decorator]
    queue=events_queue,
    exchange=steeper_exchange,
)
async def handle_realtime_event(body: dict[str, Any]) -> None:
    """
    FastStream subscriber that listens for all chat-related events
    on the steeper.events topic exchange.

    Routing key format:
        workspace.{workspace_id}.bot.{bot_id}.chat.{chat_id}.{event_type}

    The chat_id is extracted from the message body (preferred) or
    from the routing key as a fallback.
    """
    chat_id = body.get("chat_id")

    if not chat_id:
        logger.warning("Received event without chat_id, skipping: %s", body)
        return

    manager = get_connection_manager()
    await manager.broadcast_to_chat(str(chat_id), body)
    logger.debug("Broadcasted event to chat %s", chat_id)
