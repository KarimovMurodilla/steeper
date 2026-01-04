from loggers import get_logger
from src.core.database.repositories import BaseRepository
from src.marketing.models import BroadcastDelivery

logger = get_logger(__name__)


class BroadcastDeliveryRepository(BaseRepository[BroadcastDelivery]):
    model = BroadcastDelivery
