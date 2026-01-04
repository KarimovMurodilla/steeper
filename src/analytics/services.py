from src.analytics.models import AuditLog
from src.analytics.repositories import AuditLogRepository
from src.analytics.schemas import AuditLogViewModel, CreateAuditLogModel
from src.core.schemas import Base
from src.core.services import BaseService


class AuditLogService(
    BaseService[
        AuditLog, CreateAuditLogModel, Base, AuditLogRepository, AuditLogViewModel
    ]
):
    def __init__(
        self,
        repository: AuditLogRepository,
    ):
        super().__init__(repository, response_schema=AuditLogViewModel)
