import asyncio
import time
from typing import cast

from fastapi import Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from redis.asyncio import Redis

from loggers import get_logger
from src.core.errors.exceptions import UnauthorizedException
from src.realtime.dependencies import get_connection_manager
from src.realtime.enums import EventType, WSAction
from src.realtime.manager import ConnectionManager
from src.realtime.schemas import WSDownlinkEnvelope, WSErrorPayload, WSUplinkMessage
from src.user.auth.dependencies import verify_jti

logger = get_logger(__name__)

AUTH_TIMEOUT_SECONDS = 5


class WebsocketEndpointUseCase:
    """
    Use case for handling the WebSocket gateway connection and message loop.
    """

    def __init__(self, manager: ConnectionManager) -> None:
        self.manager = manager

    async def _authenticate_ws(
        self,
        websocket: WebSocket,
        redis_client: Redis,
    ) -> bool:
        """Wait for an 'authenticate' action and validate the JWT."""
        try:
            raw = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=AUTH_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            logger.debug("WS auth timeout")
            return False
        except WebSocketDisconnect:
            return False

        try:
            msg = WSUplinkMessage.model_validate(raw)
        except ValidationError:
            return False

        if msg.action != WSAction.AUTHENTICATE or not msg.token:
            return False

        try:
            await verify_jti(msg.token, redis_client)
        except UnauthorizedException:
            return False

        return True

    async def _send_error(self, websocket: WebSocket, code: int, message: str) -> None:
        """Send a system.error downlink envelope to the client."""
        error_payload = WSErrorPayload(code=code, message=message)
        envelope = WSDownlinkEnvelope(
            event=EventType.ERROR,
            workspace_id="",
            bot_id="",
            chat_id="",
            timestamp=int(time.time()),
            data=error_payload.model_dump(),
        )
        await websocket.send_json(envelope.model_dump())

    async def execute(self, websocket: WebSocket) -> None:
        """Execute the main lifecycle of the WebSocket connection."""
        await websocket.accept()

        redis_client = getattr(websocket.app.state, "redis_client", None)
        if redis_client is None:
            await self._send_error(websocket, 1011, "Service unavailable")
            await websocket.close(code=1011, reason="Service unavailable")
            return

        redis_client = cast(Redis, redis_client)

        authenticated = await self._authenticate_ws(websocket, redis_client)
        if not authenticated:
            await websocket.close(code=1008, reason="Policy Violation")
            return

        try:
            while True:
                raw = await websocket.receive_json()

                try:
                    msg = WSUplinkMessage.model_validate(raw)
                except ValidationError:
                    await self._send_error(websocket, 4000, "Invalid message format")
                    continue

                if msg.action == WSAction.SUBSCRIBE:
                    if msg.chat_id:
                        await self.manager.subscribe_chat(websocket, msg.chat_id)
                    if msg.bot_id:
                        await self.manager.subscribe_bot(websocket, msg.bot_id)

                    if not msg.chat_id and not msg.bot_id:
                        await self._send_error(
                            websocket, 4001, "chat_id or bot_id required for subscribe"
                        )

                elif msg.action == WSAction.UNSUBSCRIBE:
                    if msg.chat_id:
                        await self.manager.unsubscribe_chat(websocket, msg.chat_id)
                    if msg.bot_id:
                        await self.manager.unsubscribe_bot(websocket, msg.bot_id)

                    if not msg.chat_id and not msg.bot_id:
                        await self._send_error(
                            websocket,
                            4001,
                            "chat_id or bot_id required for unsubscribe",
                        )

                elif msg.action == WSAction.PING:
                    await websocket.send_json({"action": "pong"})

                elif msg.action == WSAction.TYPING:
                    pass

                else:
                    await self._send_error(
                        websocket, 4002, f"Unknown action: {msg.action}"
                    )

        except WebSocketDisconnect:
            logger.debug("WS disconnected")
        except Exception:
            logger.exception("Unexpected WS error")
        finally:
            self.manager.disconnect(websocket)


def get_websocket_endpoint_use_case(
    manager: ConnectionManager = Depends(get_connection_manager),
) -> WebsocketEndpointUseCase:
    return WebsocketEndpointUseCase(manager=manager)
