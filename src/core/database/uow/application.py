from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.repositories import AuditLogRepository
from src.bot.repositories.admin_bot_role import AdminBotRoleRepository
from src.bot.repositories.bot import BotRepository
from src.communication.repositories.chat import ChatRepository
from src.communication.repositories.message import MessageRepository
from src.core.database.repositories import BaseRepository
from src.core.database.uow.abstract import R, RepositoryProtocol
from src.core.database.uow.sqlalchemy import RepositoryInstance, SQLAlchemyUnitOfWork
from src.crm.repositories import TelegramUserRepository
from src.marketing.repositories.broadcast import BroadcastRepository
from src.marketing.repositories.broadcast_delivery import BroadcastDeliveryRepository
from src.user.repositories import UserRepository
from src.workspace.repositories.workspace import WorkspaceRepository
from src.workspace.repositories.workspace_member import WorkspaceMemberRepository


class ApplicationUnitOfWork(SQLAlchemyUnitOfWork[R]):
    """
    Application-specific Unit of Work implementation.

    This class extends SQLAlchemyUnitOfWork and provides repository factory methods
    for all repositories used in the application.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the ApplicationUnitOfWork with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy AsyncSession to use for database operations
        """
        super().__init__(session)
        self._repositories: dict[type[BaseRepository[Any]], BaseRepository[Any]] = {}

    def _get_repository(
        self, repository_type: type[RepositoryInstance]
    ) -> RepositoryInstance:
        """
        Get or create a repository of the specified type.

        This method implements a caching mechanism for repositories
        to avoid creating multiple instances of the same repository.

        Args:
            repository_type: The repository class to get or create

        Returns:
            An instance of the specified repository type
        """
        if repository_type not in self._repositories:
            self._repositories[repository_type] = repository_type()

        return cast(RepositoryInstance, self._repositories[repository_type])

    @property
    def users(self) -> UserRepository:
        """
        Get the UserRepository.

        Returns:
            UserRepository: The user repository
        """
        return self._get_repository(UserRepository)

    @property
    def audit_logs(self) -> AuditLogRepository:
        return self._get_repository(AuditLogRepository)

    @property
    def bots(self) -> BotRepository:
        return self._get_repository(BotRepository)

    @property
    def admin_bot_roles(self) -> AdminBotRoleRepository:
        return self._get_repository(AdminBotRoleRepository)

    @property
    def chats(self) -> ChatRepository:
        return self._get_repository(ChatRepository)

    @property
    def messages(self) -> MessageRepository:
        return self._get_repository(MessageRepository)

    @property
    def telegram_users(self) -> TelegramUserRepository:
        return self._get_repository(TelegramUserRepository)

    @property
    def broadcasts(self) -> BroadcastRepository:
        return self._get_repository(BroadcastRepository)

    @property
    def broadcast_deliveries(self) -> BroadcastDeliveryRepository:
        return self._get_repository(BroadcastDeliveryRepository)

    @property
    def workspaces(self) -> WorkspaceRepository:
        return self._get_repository(WorkspaceRepository)
    
    @property
    def workspace_members(self) -> WorkspaceMemberRepository:
        return self._get_repository(WorkspaceMemberRepository)


async def get_uow(session: AsyncSession) -> ApplicationUnitOfWork[RepositoryProtocol]:
    """
    Dependency injection function to get an ApplicationUnitOfWork instance.

    Args:
        session: The SQLAlchemy AsyncSession to use for database operations

    Returns:
        ApplicationUnitOfWork: The UnitOfWork instance
    """
    return ApplicationUnitOfWork(session)
