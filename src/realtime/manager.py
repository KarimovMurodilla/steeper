from collections import defaultdict
import logging
from typing import Any

from fastapi.websockets import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager with O(1) disconnect cleanup.

    Maintains a bi-directional mapping between chat IDs and WebSocket connections
    to guarantee constant-time cleanup when a client disconnects.
    """

    def __init__(self) -> None:
        # chat_id -> set of WebSockets
        self.subscriptions: dict[str, set[WebSocket]] = defaultdict(set)
        # WebSocket -> set of chat_ids (Reverse map for fast cleanup)
        self.active_connections: dict[WebSocket, set[str]] = defaultdict(set)

    async def subscribe(self, websocket: WebSocket, chat_id: str) -> None:
        """Subscribe a WebSocket connection to a chat channel."""
        self.subscriptions[chat_id].add(websocket)
        self.active_connections[websocket].add(chat_id)
        logger.debug("WS subscribed to chat %s", chat_id)

    async def unsubscribe(self, websocket: WebSocket, chat_id: str) -> None:
        """Unsubscribe a WebSocket connection from a chat channel."""
        if websocket in self.subscriptions.get(chat_id, set()):
            self.subscriptions[chat_id].discard(websocket)
            if not self.subscriptions[chat_id]:
                del self.subscriptions[chat_id]

        self.active_connections[websocket].discard(chat_id)
        if not self.active_connections[websocket]:
            del self.active_connections[websocket]

        logger.debug("WS unsubscribed from chat %s", chat_id)

    def disconnect(self, websocket: WebSocket) -> None:
        """O(1) disconnect cleanup using reverse mapping."""
        chat_ids = self.active_connections.pop(websocket, set())
        for chat_id in chat_ids:
            if websocket in self.subscriptions.get(chat_id, set()):
                self.subscriptions[chat_id].discard(websocket)

            # Clean up empty sets
            if not self.subscriptions.get(chat_id):
                self.subscriptions.pop(chat_id, None)

        logger.debug("WS disconnected, cleaned up %d subscriptions", len(chat_ids))

    async def broadcast_to_chat(self, chat_id: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all WebSocket connections subscribed to a chat."""
        connections = self.subscriptions.get(chat_id, set())
        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)
