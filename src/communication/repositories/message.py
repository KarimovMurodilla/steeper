from loggers import get_logger
from src.communication.models import Message
from src.core.database.repositories import BaseRepository

logger = get_logger(__name__)


class MessageRepository(BaseRepository[Message]):
    model = Message
