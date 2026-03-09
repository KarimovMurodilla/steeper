Technical Specification: Real-Time Messaging System (Steeper)

1. Overview

The system provides real-time message delivery and UI synchronization for the Steeper platform. It connects Telegram users, Backend services (FastAPI + Celery), and the Admin dashboard (Web UI).

To comply with the project's strict multi-tenant architecture and to support horizontal scaling, all real-time events pass through an Event Bus.

Core Architectural Decisions:

WebSocket (WS) is strictly for receiving data (Downlink). Sending messages from the UI is performed via HTTP REST API to ensure reliable delivery, rate-limiting, and state management.

Stateless WS Gateways: Each WebSocket server instance maintains only its local connection state.

Broker Abstraction (FastStream): The system uses FastStream to abstract the underlying message broker. While RabbitMQ is the initial implementation, this abstraction guarantees a near-zero-rewrite migration path to Apache Kafka in the future.

2. System Architecture

[ Telegram API ]
       │
       ▼ (Webhook)
[ FastAPI Backend ] ──────(HTTP POST /messages)────── [ Admin Web UI ]
       │                                                     │
       ▼ (Save to DB via UoW & dispatch task)                │
[ Celery Workers ]                                           │
       │                                                     │
       ▼ (Publish Event via FastStream)                      │
[ Event Bus (RabbitMQ -> Future: Kafka) ]                    │
       │                                                     │
       ├── [ WS Gateway 1 ] ─────(WebSocket Stream)──────────┤
       └── [ WS Gateway N ] ─────(WebSocket Stream)──────────┘


3. Event Bus & Routing (FastStream)

Technology: RabbitMQ (via FastStream RabbitBroker)
Exchange type: topic (e.g., steeper.events)

3.1 Multi-tenant Routing Keys

To avoid querying the database on every event, the routing key MUST contain the domain hierarchy. This allows Gateways to subscribe selectively and paves the way for Kafka partitioning keys.

Format:
workspace.{workspace_id}.bot.{bot_id}.chat.{chat_id}.{event_type}

Examples:

workspace.123e4567.bot.987fcdeb.chat.555.message.created

workspace.123e4567.bot.987fcdeb.chat.555.typing

Subscription Strategy:
When an admin connects and selects a workspace, the Gateway subscribes dynamically to workspace.{workspace_id}.#. FastStream handles the underlying AMQP queue creation and bindings automatically.

3.2 Future-proofing for Kafka

Because we use FastStream, migrating to Kafka will simply require swapping RabbitBroker for KafkaBroker. The topic wildcard workspace.{workspace_id}.# will be refactored into a single Kafka topic (e.g., workspace_events), and the workspace_id will be used as the Kafka message key to ensure ordered processing and correct partitioning.

4. Connection Lifecycle & Security

4.1 Authentication (No Params in URL)

Passing JWT tokens in the WS URL (ws://api/ws?token=JWT) is forbidden due to security risks (URL logging).

Client opens connection: ws://api.steeper.com/v1/ws

Server accepts connection but sets a 5-second timeout.

Client MUST immediately send an authenticate payload.

Server validates the JWT against Redis/DB. If invalid or timeout expires, server closes connection with status 1008 Policy Violation.

4.2 Reconnection & Message Recovery

WebSockets are volatile.
Rule: The WS Gateway does NOT store missed messages.
Upon any WS reconnection, the Frontend MUST fetch missed messages via REST API using cursor-based pagination:
GET /v1/bots/{bot_id}/chats/{chat_id}/messages?limit=50&cursor={last_message_id}

5. WebSocket Protocol Contract

All WS messages are validated via Pydantic Models enforcing strict typing.

5.1 Enums Registry (src/realtime/enums.py)

from enum import StrEnum

class EventType(StrEnum):
    CHAT_MESSAGE_CREATED = "chat.message.created"
    CHAT_MESSAGE_UPDATED = "chat.message.updated"
    CHAT_MESSAGE_DELETED = "chat.message.deleted"
    CHAT_TYPING = "chat.typing"
    ERROR = "system.error"

class WSAction(StrEnum):
    AUTHENTICATE = "authenticate"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    TYPING = "typing"
    PING = "ping"


5.2 Server → Client (Downlink Envelope)

{
  "version": 1,
  "event": "chat.message.created",
  "workspace_id": "uuid",
  "bot_id": "uuid",
  "chat_id": "uuid",
  "timestamp": 1710000000,
  "data": {
    "message_id": "msg_uuid",
    "text": "Hello, support!"
  }
}


5.3 Client → Server (Uplink Actions)

{
  "action": "subscribe",
  "chat_id": "uuid"
}


6. Connection Manager (O(1) Complexity)

To prevent $O(N)$ memory leaks and CPU spikes during disconnects, the connection manager MUST maintain a reverse mapping of connections.

# src/realtime/manager.py
from collections import defaultdict
from fastapi.websockets import WebSocket

class ConnectionManager:
    def __init__(self) -> None:
        # chat_id -> set of WebSockets
        self.subscriptions: dict[str, set[WebSocket]] = defaultdict(set)
        # WebSocket -> set of chat_ids (Reverse map for fast cleanup)
        self.active_connections: dict[WebSocket, set[str]] = defaultdict(set)

    async def subscribe(self, websocket: WebSocket, chat_id: str) -> None:
        self.subscriptions[chat_id].add(websocket)
        self.active_connections[websocket].add(chat_id)

    def disconnect(self, websocket: WebSocket) -> None:
        """O(1) disconnect cleanup using reverse mapping."""
        chat_ids = self.active_connections.pop(websocket, set())
        for chat_id in chat_ids:
            if websocket in self.subscriptions.get(chat_id, set()):
                self.subscriptions[chat_id].remove(websocket)

            # Clean up empty sets
            if not self.subscriptions[chat_id]:
                del self.subscriptions[chat_id]

    async def broadcast_to_chat(self, chat_id: str, message: dict) -> None:
        connections = self.subscriptions.get(chat_id, set())
        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


7. Sending Messages (Admin to User)

Flow:

Admin clicks "Send" in UI.

Frontend calls POST /v1/communications/webhook/{token_hash}/bot-message.

FastAPI validates request and creates a Celery Task.

FastAPI returns 202 Accepted (or 200 OK) to Frontend. UI shows a "queued" clock icon 🕒.

Celery Worker sends message to Telegram API.

Upon success, Worker uses UoW to save to DB and publishes chat.message.created to RabbitMQ via FastStream publisher.

WS Gateway receives event via FastStream @subscriber and pushes to Frontend.

Frontend replaces clock icon 🕒 with a checkmark ✓.

8. Expected Project Structure integration

Following the architecture.md principles, real-time logic will be isolated into its own domain:

src/
└── realtime/
    ├── __init__.py
    ├── broker.py         # FastStream RabbitBroker initialization
    ├── consumers.py      # FastStream @broker.subscriber(...) listeners
    ├── dependencies.py   # DI for ConnectionManager
    ├── enums.py          # EventType, WSAction
    ├── manager.py        # WebSocket ConnectionManager
    ├── routers.py        # /v1/ws endpoints
    └── schemas.py        # Pydantic models for WS payload validation


9. Performance Metrics Target

Concurrent Connections: 100k+ across multiple pods.

Event Delivery Latency: < 100ms (Telegram webhook -> FastStream -> WS Gateway -> Browser).

Memory Footprint: Reverse mapping ensures clean GC sweeps upon disconnects.
