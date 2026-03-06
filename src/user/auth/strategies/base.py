from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.user.models import User

TAuthRequest = TypeVar("TAuthRequest")
TAuthData = TypeVar("TAuthData")


class BaseAuthStrategy(ABC, Generic[TAuthRequest, TAuthData]):
    """
    Truly abstract base class for ANY authentication strategy (Telegram, Google, Apple).
    Uses Generic types so implementations can define their specific request and data formats.
    """

    @abstractmethod
    def verify(self, data: TAuthRequest) -> TAuthData:
        """Verifies the incoming request (e.g., cryptographic signature, token) and extracts user data."""
        pass

    @abstractmethod
    async def resolve_user(
        self, uow: ApplicationUnitOfWork[RepositoryProtocol], user_data: TAuthData
    ) -> User:
        """Handles the business logic of retrieving, creating, or updating the user in the database."""
        pass
