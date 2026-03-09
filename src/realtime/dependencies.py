from fastapi import Depends

from src.realtime.manager import ConnectionManager
from src.realtime.usecases.websocket_endpoint import WebsocketEndpointUseCase

_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Return the singleton ConnectionManager instance."""
    return _manager


def get_websocket_endpoint_use_case(
    manager: ConnectionManager = Depends(get_connection_manager),
) -> WebsocketEndpointUseCase:
    return WebsocketEndpointUseCase(manager=manager)
