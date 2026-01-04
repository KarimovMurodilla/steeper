from loggers import get_logger
from src.analytics.models import AuditLog
from src.core.database.repositories import BaseRepository

logger = get_logger(__name__)


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog
