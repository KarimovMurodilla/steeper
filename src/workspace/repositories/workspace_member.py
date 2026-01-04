from loggers import get_logger
from src.core.database.repositories import SoftDeleteRepository
from src.workspace.models import WorkspaceMember

logger = get_logger(__name__)


class WorkspaceMemberRepository(SoftDeleteRepository[WorkspaceMember]):
    model = WorkspaceMember
