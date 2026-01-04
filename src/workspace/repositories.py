from loggers import get_logger
from src.core.database.repositories import SoftDeleteRepository
from src.workspace.models import Workspace

logger = get_logger(__name__)


class WorkspaceRepository(SoftDeleteRepository[Workspace]):
    model = Workspace
