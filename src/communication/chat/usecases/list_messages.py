"""Use case: cursor-paginated message history for a chat."""

from uuid import UUID

from fastapi import Depends

from src.communication.schemas import (
    CursorPaginatedResponse,
    MessageListItemViewModel,
)
from src.core.database.session import get_unit_of_work
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


def get_list_messages_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListMessagesUseCase:
    return ListMessagesUseCase(uow=uow)
