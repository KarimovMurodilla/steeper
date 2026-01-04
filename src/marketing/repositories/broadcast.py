from loggers import get_logger
from src.core.database.repositories import SoftDeleteRepository
from src.marketing.models import Broadcast

logger = get_logger(__name__)


class BroadcastRepository(SoftDeleteRepository[Broadcast]):
    model = Broadcast
