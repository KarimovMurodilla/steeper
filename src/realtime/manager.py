from collections import defaultdict
import logging
from typing import Any

from fastapi.websockets import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager with O(1) disconnect cleanup.

    Supports subscribing to specific chats or entire bots (to update unread counters).
    """

    def __init__(self) -> None:
        self.chat_subscriptions: dict[str, set[WebSocket]] = defaultdict(set)
        self.active_chat_connections: dict[WebSocket, set[str]] = defaultdict(set)

        self.bot_subscriptions: dict[str, set[WebSocket]] = defaultdict(set)
        self.active_bot_connections: dict[WebSocket, set[str]] = defaultdict(set)

    async def subscribe_chat(self, websocket: WebSocket, chat_id: str) -> None:
        self.chat_subscriptions[chat_id].add(websocket)
        self.active_chat_connections[websocket].add(chat_id)
        logger.debug("WS subscribed to chat %s", chat_id)

    async def subscribe_bot(self, websocket: WebSocket, bot_id: str) -> None:
        self.bot_subscriptions[bot_id].add(websocket)
        self.active_bot_connections[websocket].add(bot_id)
        logger.debug("WS subscribed to bot %s", bot_id)

    async def unsubscribe_chat(self, websocket: WebSocket, chat_id: str) -> None:
        if websocket in self.chat_subscriptions.get(chat_id, set()):
            self.chat_subscriptions[chat_id].discard(websocket)
            if not self.chat_subscriptions[chat_id]:
                del self.chat_subscriptions[chat_id]

        self.active_chat_connections[websocket].discard(chat_id)
        if not self.active_chat_connections[websocket]:
            del self.active_chat_connections[websocket]
        logger.debug("WS unsubscribed from chat %s", chat_id)

    async def unsubscribe_bot(self, websocket: WebSocket, bot_id: str) -> None:
        if websocket in self.bot_subscriptions.get(bot_id, set()):
            self.bot_subscriptions[bot_id].discard(websocket)
            if not self.bot_subscriptions[bot_id]:
                del self.bot_subscriptions[bot_id]

        self.active_bot_connections[websocket].discard(bot_id)
        if not self.active_bot_connections[websocket]:
            del self.active_bot_connections[websocket]
        logger.debug("WS unsubscribed from bot %s", bot_id)

    def disconnect(self, websocket: WebSocket) -> None:
        """O(1) disconnect cleanup for both chat and bot subscriptions."""
        chat_ids = self.active_chat_connections.pop(websocket, set())
        for chat_id in chat_ids:
            if websocket in self.chat_subscriptions.get(chat_id, set()):
                self.chat_subscriptions[chat_id].discard(websocket)
            if not self.chat_subscriptions.get(chat_id):
                self.chat_subscriptions.pop(chat_id, None)

        bot_ids = self.active_bot_connections.pop(websocket, set())
        for bot_id in bot_ids:
            if websocket in self.bot_subscriptions.get(bot_id, set()):
                self.bot_subscriptions[bot_id].discard(websocket)
            if not self.bot_subscriptions.get(bot_id):
                self.bot_subscriptions.pop(bot_id, None)

        logger.debug(
            "WS disconnected, cleaned up %d chat subs, %d bot subs",
            len(chat_ids),
            len(bot_ids),
        )

    async def broadcast(
        self, chat_id: str | None, bot_id: str | None, message: dict[str, Any]
    ) -> None:
        """
        Broadcast a message to clients subscribed to the chat OR the bot.
        Uses a Set to prevent sending duplicate messages if a client is subscribed to both.
        """
        target_ws: set[WebSocket] = set()

        if chat_id:
            target_ws.update(self.chat_subscriptions.get(chat_id, set()))
        if bot_id:
            target_ws.update(self.bot_subscriptions.get(bot_id, set()))

        for ws in list(target_ws):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)
