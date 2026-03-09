from src.realtime.manager import ConnectionManager

_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Return the singleton ConnectionManager instance."""
    return _manager
