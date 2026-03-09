from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket

from src.realtime.dependencies import get_websocket_endpoint_use_case
from src.realtime.usecases.websocket_endpoint import (
    WebsocketEndpointUseCase,
)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    use_case: Annotated[
        WebsocketEndpointUseCase, Depends(get_websocket_endpoint_use_case)
    ],
) -> None:
    """
    WebSocket gateway endpoint.

    Lifecycle:
      1. Accept connection, enforce 5 s auth timeout.
      2. Validate JWT via Redis (reusing verify_jti).
      3. Enter message loop: handle subscribe / unsubscribe / typing / ping.
      4. On disconnect, clean up all subscriptions via ConnectionManager.
    """
    await use_case.execute(websocket)
