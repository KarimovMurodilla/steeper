"""Use case: list chats for a bot."""

from uuid import UUID

from fastapi import Depends

from src.communication.schemas import ChatListItemViewModel
from src.core.database.session import get_unit_of_work
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork
from src.core.pagination import (
    PaginatedResponse,
    PaginationParams,
    make_paginated_response,
)


class ListChatsUseCase:
    """Returns a paginated list of chats for a given bot."""

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(
        self,
        bot_id: UUID,
        pagination: PaginationParams,
    ) -> PaginatedResponse[ChatListItemViewModel]:
        async with self.uow as uow:
            chats, total = await uow.chats.get_paginated_by_bot(
                uow.session,
                bot_id=bot_id,
                page=pagination.page,
                size=pagination.size,
            )

            items: list[ChatListItemViewModel] = []
            for chat in chats:
                last_msg = await uow.chats.get_last_message_content(
                    uow.session, chat.id
                )
                items.append(
                    ChatListItemViewModel(
                        chat_id=chat.id,
                        telegram_id=chat.telegram_user.tg_user_id,
                        first_name=chat.telegram_user.first_name,
                        username=chat.telegram_user.username,
                        last_message=last_msg,
                        updated_at=chat.updated_at,
                    )
                )

        return make_paginated_response(items=items, total=total, pagination=pagination)


def get_list_chats_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListChatsUseCase:
    return ListChatsUseCase(uow=uow)
