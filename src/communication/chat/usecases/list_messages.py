"""Use case: cursor-paginated message history for a chat."""

from uuid import UUID

from src.communication.schemas import (
    CursorPaginatedResponse,
    MessageListItemViewModel,
)
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork


class ListMessagesUseCase:
    """Returns cursor-paginated messages for a chat (newest first)."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(
        self,
        chat_id: UUID,
        limit: int = 50,
        cursor: UUID | None = None,
    ) -> CursorPaginatedResponse[MessageListItemViewModel]:
        """
        Executes the business logic for listing cursor-paginated messages of a chat.

        Args:
            chat_id (UUID): The unique identifier of the chat.
            limit (int, optional): The maximum number of messages to fetch. Defaults to 50.
            cursor (UUID | None, optional): The cursor for pagination. Defaults to None.

        Returns:
            CursorPaginatedResponse[MessageListItemViewModel]: The cursor-paginated items.
        """
        async with self.uow as uow:
            messages = await uow.messages.get_cursor_paginated(
                uow.session,
                chat_id=chat_id,
                limit=limit,
                cursor=cursor,
            )

        items = [
            MessageListItemViewModel(
                id=msg.id,
                sender=msg.sender_type,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ]

        next_cursor = str(items[-1].id) if len(items) == limit else None

        return CursorPaginatedResponse[MessageListItemViewModel](
            items=items,
            next_cursor=next_cursor,
        )
